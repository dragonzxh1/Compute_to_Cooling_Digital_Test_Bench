using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

// External read-only target Job verifier. No Python FFI/import needed by target.
public static class VerifyTarget {
    [StructLayout(LayoutKind.Sequential)] struct Basic {
        public long ProcessTime,JobTime; public uint Flags;
        public UIntPtr MinWorking,MaxWorking; public uint Active;
        public UIntPtr Affinity; public uint Priority,Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IO {
        public ulong ReadOps,WriteOps,OtherOps,ReadBytes,WriteBytes,OtherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct Extended {
        public Basic Basic; public IO IO; public UIntPtr ProcessMemory,JobMemory,PeakProcess,PeakJob;
    }
    [StructLayout(LayoutKind.Sequential)] struct CPU { public uint Flags,Rate; }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr OpenJobObjectW(uint access,bool inherit,string name);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool belongs);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool QueryInformationJobObject(IntPtr job,int kind,IntPtr data,uint size,IntPtr returned);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    static T Query<T>(IntPtr job,int kind) {
        IntPtr p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));
        try {
            if(!QueryInformationJobObject(job,kind,p,(uint)Marshal.SizeOf(typeof(T)),IntPtr.Zero))
                throw new InvalidOperationException("JOB_LIMIT_QUERY_FAILED");
            return (T)Marshal.PtrToStructure(p,typeof(T));
        } finally { Marshal.FreeHGlobal(p); }
    }
    static string Json(string text) { return "\""+text.Replace("\\","\\\\").Replace("\"","\\\"")+"\""; }
    public static int Main(string[] args) {
        if(Environment.GetEnvironmentVariable("GITHUB_ACTIONS")!="true" ||
           Environment.GetEnvironmentVariable("RUNNER_ENVIRONMENT")!="github-hosted" ||
           Environment.GetEnvironmentVariable("RUNNER_OS")!="Windows" ||
           Environment.MachineName.Equals("HIPPO",StringComparison.OrdinalIgnoreCase))return 129;
        if(args.Length!=6 || args[5]!="10000" || args[2]!="4096" || args[3]!="8192") return 125;
        // named Job, actual PID, expected process MB, job MB, proof path, expected CPU rate
        IntPtr job=IntPtr.Zero,process=IntPtr.Zero;
        try {
            if(IntPtr.Size!=8 || Marshal.SizeOf(typeof(Basic))!=64 || Marshal.SizeOf(typeof(Extended))!=144 || Marshal.SizeOf(typeof(CPU))!=8)
                throw new InvalidOperationException("UNSUPPORTED_ABI");
            job=OpenJobObjectW(4,false,args[0]);process=OpenProcess(0x1000,false,uint.Parse(args[1]));
            bool belongs;
            if(job==IntPtr.Zero || process==IntPtr.Zero || !IsProcessInJob(process,job,out belongs) || !belongs)
                throw new InvalidOperationException("ACTUAL_PYTHON_NOT_IN_TARGET_JOB");
            Extended e=Query<Extended>(job,9);CPU cpu=Query<CPU>(job,15);
            if(e.Basic.Flags!=0x2308 || e.Basic.Active!=4 || cpu.Flags!=5 || cpu.Rate!=uint.Parse(args[5]) ||
               e.ProcessMemory.ToUInt64()!=ulong.Parse(args[2])*1024*1024 || e.JobMemory.ToUInt64()!=ulong.Parse(args[3])*1024*1024)
                throw new InvalidOperationException("TARGET_JOB_LIMITS_MISMATCH");
            StringBuilder modules=new StringBuilder("[");bool first=true;
            using(Process p=Process.GetProcessById(int.Parse(args[1]))) {
                foreach(ProcessModule m in p.Modules) {
                    if(!first) modules.Append(',');first=false;
                    modules.Append(Json(m.ModuleName));
                }
            }
            modules.Append(']');
            string proof="{\"actual_python_pid\":"+args[1]+",\"in_target_job\":true,\"target_job_name\":"+Json(args[0])+
                ",\"cpu_rate\":"+cpu.Rate+",\"cpu_flags\":5,\"basic_flags\":8968,\"max_active_processes\":4,\"process_mb\":"+args[2]+
                ",\"job_mb\":"+args[3]+",\"modules_before_workload\":"+modules+"}";
            using(FileStream f=new FileStream(args[4],FileMode.CreateNew,FileAccess.Write,FileShare.Read)) {
                byte[] bytes=Encoding.UTF8.GetBytes(proof+"\n");f.Write(bytes,0,bytes.Length);f.Flush(true);
            }
            return 0;
        } catch(Exception ex) { Console.Error.WriteLine(ex.GetType().Name+": "+ex.Message);return 125; }
        finally { if(process!=IntPtr.Zero)CloseHandle(process);if(job!=IntPtr.Zero)CloseHandle(job); }
    }
}
