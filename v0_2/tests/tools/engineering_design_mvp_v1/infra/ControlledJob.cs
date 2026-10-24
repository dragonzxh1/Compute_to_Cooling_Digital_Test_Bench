using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

// User-owned child jobs only. No power, driver, firmware or device operations.
public static class ControlledJob {
    const uint Suspended=4, NoWindow=0x08000000, UseStdHandles=0x100;
    const uint KillOnClose=0x2000, ProcessMemory=0x100, JobMemory=0x200, ActiveLimit=8;
    static volatile bool Cancelled;
    [StructLayout(LayoutKind.Sequential)] struct Basic {
        public long ProcessTime, JobTime; public uint Flags;
        public UIntPtr MinWorking, MaxWorking; public uint ActiveProcesses;
        public UIntPtr Affinity; public uint Priority, Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IO {
        public ulong ReadOps,WriteOps,OtherOps,ReadBytes,WriteBytes,OtherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct Extended {
        public Basic Basic; public IO IO; public UIntPtr ProcessMemory,JobMemory,PeakProcess,PeakJob;
    }
    [StructLayout(LayoutKind.Sequential)] struct CPU { public uint Flags,Rate; }
    [StructLayout(LayoutKind.Sequential)] struct Accounting {
        public long User,Kernel,PeriodUser,PeriodKernel;
        public uint Faults,Total,Active,Terminated;
    }
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct Startup {
        public uint cb; public IntPtr Reserved,Desktop,Title;
        public uint X,Y,XSize,YSize,XCount,YCount,Fill,Flags;
        public ushort Show,ReservedSize; public IntPtr ReservedData,Input,Output,Error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo {
        public IntPtr Process,Thread; public uint ProcessId,ThreadId;
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateJobObjectW(IntPtr security,string name);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool SetInformationJobObject(IntPtr job,int kind,IntPtr data,uint size);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool QueryInformationJobObject(IntPtr job,int kind,IntPtr data,uint size,IntPtr returned);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32.dll",SetLastError=true)]
    static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool CreateProcessW(string application,StringBuilder command,IntPtr psa,IntPtr tsa,
        bool inherit,uint flags,IntPtr environment,string cwd,ref Startup startup,out ProcessInfo process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int which);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);

    static void Check(bool ok,string name) { if(!ok) throw new Win32Exception(Marshal.GetLastWin32Error(),name); }
    static void Set<T>(IntPtr job,int kind,T value) {
        IntPtr p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));
        try { Marshal.StructureToPtr(value,p,false); Check(SetInformationJobObject(job,kind,p,(uint)Marshal.SizeOf(typeof(T))),"SetInformationJobObject"); }
        finally { Marshal.FreeHGlobal(p); }
    }
    static T Query<T>(IntPtr job,int kind) {
        IntPtr p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));
        try { Check(QueryInformationJobObject(job,kind,p,(uint)Marshal.SizeOf(typeof(T)),IntPtr.Zero),"QueryInformationJobObject"); return (T)Marshal.PtrToStructure(p,typeof(T)); }
        finally { Marshal.FreeHGlobal(p); }
    }
    static string Quote(string value) {
        if(value.Length>0 && value.IndexOfAny(new char[]{' ','\t','"','\n'})<0) return value;
        StringBuilder b=new StringBuilder("\""); int slashes=0;
        foreach(char c in value) {
            if(c=='\\') { slashes++; continue; }
            if(c=='\"') { b.Append('\\',slashes*2+1); b.Append(c); }
            else { b.Append('\\',slashes); b.Append(c); }
            slashes=0;
        }
        b.Append('\\',slashes*2); b.Append('"'); return b.ToString();
    }
    static string Json(string value) {
        return "\""+value.Replace("\\","\\\\").Replace("\"","\\\"").Replace("\r","\\r").Replace("\n","\\n").Replace("\t","\\t")+"\"";
    }
    static void Exclusive(string path,string text) {
        using(FileStream f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)) {
            byte[] data=Encoding.UTF8.GetBytes(text+"\n"); f.Write(data,0,data.Length); f.Flush(true);
        }
    }
    static void Layouts() {
        if(IntPtr.Size!=8 || Marshal.SizeOf(typeof(Basic))!=64 || Marshal.SizeOf(typeof(Extended))!=144 ||
           Marshal.SizeOf(typeof(CPU))!=8 || Marshal.SizeOf(typeof(Accounting))!=48 ||
           Marshal.SizeOf(typeof(Startup))!=104 || Marshal.SizeOf(typeof(ProcessInfo))!=24)
            throw new InvalidOperationException("UNSUPPORTED_NATIVE_ABI");
    }
    static long Length(string path) { return File.Exists(path)?new FileInfo(path).Length:0; }

    public static int Main(string[] args) {
        if(Environment.GetEnvironmentVariable("GITHUB_ACTIONS")!="true" ||
           Environment.GetEnvironmentVariable("RUNNER_ENVIRONMENT")!="github-hosted" ||
           Environment.GetEnvironmentVariable("RUNNER_OS")!="Windows" ||
           Environment.MachineName.Equals("HIPPO",StringComparison.OrdinalIgnoreCase)) {
            Console.Error.WriteLine("INDEPENDENT_HOSTED_WINDOWS_REQUIRED");return 129;
        }
        if(args.Length==1 && args[0]=="--layout-selftest") {
            Layouts(); Console.WriteLine("NATIVE_LAYOUTS_PASS_NO_CHILD_LAUNCHED"); return 0;
        }
        // status, start-record, cancellation-file, stdout-file, stderr-file,
        // wall-ms, CPU/10000, process-MB, job-MB, executable, [arguments...]
        if(args.Length<10) { Console.Error.WriteLine("CONTROLLED_JOB_ARGUMENTS_REQUIRED"); return 125; }
        string status=args[0],startFile=args[1],cancelFile=args[2],outFile=args[3],errFile=args[4];
        int wall; uint rate; ulong processMB,jobMB;
        if(!int.TryParse(args[5],out wall) || wall<1 || wall>480000 ||
           !uint.TryParse(args[6],out rate) || rate!=10000 ||
           !ulong.TryParse(args[7],out processMB) ||
           !ulong.TryParse(args[8],out jobMB) ||
           !(processMB==4096 && jobMB==8192) || !Path.IsPathRooted(args[9])) {
            Console.Error.WriteLine("SAFE_RESOURCE_POLICY_REJECTED"); return 125;
        }
        IntPtr job=IntPtr.Zero; ProcessInfo pi=new ProcessInfo(); Mutex mutex=null;
        bool owned=false,assigned=false,resumed=false,cleanupOK=true; string outcome="SETUP_FAILURE",error="";
        uint childCode=0,active=0; int answer=125; Stopwatch clock=Stopwatch.StartNew();
        try {
            Layouts(); mutex=new Mutex(false,"Global\\C2CDTB_Development_Execution");
            try { owned=mutex.WaitOne(0); }
            catch(AbandonedMutexException) { owned=true; throw new InvalidOperationException("PREVIOUS_EXECUTOR_ABANDONED_REVIEW_REQUIRED"); }
            if(!owned) { outcome="BUSY"; answer=126; return answer; }
            if(File.Exists(cancelFile)) { outcome="CANCELLED_BEFORE_LAUNCH"; answer=122; return answer; }
            string jobName="Local\\C2CDTB_OwnedJob_"+Guid.NewGuid().ToString("N");
            job=CreateJobObjectW(IntPtr.Zero,jobName); Check(job!=IntPtr.Zero,"CreateJobObjectW");
            if(Marshal.GetLastWin32Error()==183) throw new InvalidOperationException("OWNED_JOB_NAME_COLLISION");
            Extended limits=new Extended();
            limits.Basic.Flags=KillOnClose|ProcessMemory|JobMemory|ActiveLimit;
            limits.Basic.ActiveProcesses=4;
            limits.ProcessMemory=new UIntPtr(processMB*1024*1024); limits.JobMemory=new UIntPtr(jobMB*1024*1024);
            Set(job,9,limits); Set(job,15,new CPU {Flags=1|4,Rate=rate});
            Extended checkedLimits=Query<Extended>(job,9); CPU checkedCPU=Query<CPU>(job,15);
            if(checkedLimits.Basic.Flags!=limits.Basic.Flags || checkedLimits.ProcessMemory!=limits.ProcessMemory ||
               checkedLimits.JobMemory!=limits.JobMemory || checkedCPU.Flags!=5 || checkedCPU.Rate!=rate)
                throw new InvalidOperationException("RESOURCE_LIMIT_READBACK_FAILED");
            Startup startup=new Startup(); startup.cb=(uint)Marshal.SizeOf(typeof(Startup)); startup.Flags=UseStdHandles;
            startup.Input=GetStdHandle(-10); startup.Output=GetStdHandle(-11); startup.Error=GetStdHandle(-12);
            StringBuilder command=new StringBuilder();
            for(int i=9;i<args.Length;i++) { if(i>9) command.Append(' '); command.Append(Quote(args[i])); }
            Check(CreateProcessW(args[9],command,IntPtr.Zero,IntPtr.Zero,true,Suspended|NoWindow,IntPtr.Zero,
                Environment.CurrentDirectory,ref startup,out pi),"CreateProcessW_SUSPENDED");
            Check(AssignProcessToJobObject(job,pi.Process),"AssignProcessToJobObject"); assigned=true;
            Exclusive(startFile,"{\"pid\":"+pi.ProcessId+",\"assigned_before_resume\":true,\"cpu_rate\":"+rate+
                ",\"process_memory_mb\":"+processMB+",\"job_memory_mb\":"+jobMB+",\"wall_ms\":"+wall+
                ",\"kill_on_close\":true,\"job_name\":"+Json(jobName)+",\"job_identity_version\":2}");
            Console.CancelKeyPress+=(s,e)=>{Cancelled=true;e.Cancel=true;};
            if(ResumeThread(pi.Thread)==0xFFFFFFFF) throw new Win32Exception(Marshal.GetLastWin32Error(),"ResumeThread");
            resumed=true; CloseHandle(pi.Thread); pi.Thread=IntPtr.Zero;
            long nextHeartbeat=1000; int heartbeat=0;
            while(true) {
                uint wait=WaitForSingleObject(pi.Process,40);
                if(wait==0) {
                    Check(GetExitCodeProcess(pi.Process,out childCode),"GetExitCodeProcess"); outcome="EXITED";answer=0;
                    if(Length(outFile)+Length(errFile)>2*1024*1024) { outcome="OUTPUT_LIMIT";answer=123; }
                    break;
                }
                if(wait!=258) throw new Win32Exception(Marshal.GetLastWin32Error(),"WaitForSingleObject");
                if(clock.ElapsedMilliseconds>=nextHeartbeat) {
                    Accounting a=Query<Accounting>(job,1); Extended e=Query<Extended>(job,9);
                    Exclusive(startFile+".heartbeat-"+(heartbeat++).ToString("D3")+".json",
                        "{\"pid\":"+pi.ProcessId+",\"elapsed_ms\":"+clock.ElapsedMilliseconds+
                        ",\"job_cpu_100ns\":"+(a.User+a.Kernel)+",\"active\":"+a.Active+
                        ",\"peak_job_memory_bytes\":"+e.PeakJob.ToUInt64()+"}");
                    nextHeartbeat=clock.ElapsedMilliseconds+1000;
                }
                if(Cancelled || File.Exists(cancelFile)) { outcome="CANCELLED";answer=122;break; }
                if(clock.ElapsedMilliseconds>=wall) { outcome="TIMEOUT";answer=124;break; }
                if(Length(outFile)+Length(errFile)>2*1024*1024) { outcome="OUTPUT_LIMIT";answer=123;break; }
            }
        } catch(Exception ex) { error=ex.GetType().Name+": "+ex.Message; answer=125; }
        finally {
            // Terminate our JOB even after launcher success: descendants cannot outlive it.
            if(job!=IntPtr.Zero) {
                bool terminated=TerminateJobObject(job,1);
                Stopwatch grace=Stopwatch.StartNew();
                try {
                    do { active=Query<Accounting>(job,1).Active; if(active==0) break; Thread.Sleep(20); }
                    while(grace.ElapsedMilliseconds<2000);
                    cleanupOK=active==0;
                    if(!terminated && active!=0) cleanupOK=false;
                } catch(Exception ex) { cleanupOK=false;error+="; cleanup "+ex.GetType().Name; }
                CloseHandle(job); job=IntPtr.Zero; // OS kill-on-close also covers supervisor death.
            }
            if(pi.Process!=IntPtr.Zero) {
                if(!assigned && !TerminateProcess(pi.Process,1)) { cleanupOK=false;error+="; suspended child termination failed"; }
                if(WaitForSingleObject(pi.Process,2000)!=0) cleanupOK=false;
                CloseHandle(pi.Process);
            }
            if(pi.Thread!=IntPtr.Zero) CloseHandle(pi.Thread);
            if(!cleanupOK) { outcome="CLEANUP_FAILED";answer=127; }
            try {
                Exclusive(status,"{\"outcome\":"+Json(outcome)+",\"child_exitcode\":"+childCode+
                    ",\"pid\":"+pi.ProcessId+",\"assigned_before_resume\":"+(assigned?"true":"false")+
                    ",\"resumed\":"+(resumed?"true":"false")+",\"cleanup_complete\":"+(cleanupOK?"true":"false")+
                    ",\"active_after_cleanup\":"+active+",\"error\":"+Json(error)+"}");
            } catch(Exception ex) { Console.Error.WriteLine("CONTROL_STATUS_PERSISTENCE_FAILED "+ex.GetType().Name);answer=128; }
            if(owned && mutex!=null) mutex.ReleaseMutex();
            if(mutex!=null) mutex.Dispose();
        }
        return answer;
    }
}
