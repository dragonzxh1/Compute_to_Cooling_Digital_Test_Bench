"""Finite streaming physical evidence; no decimation of adverse intervals."""
import json,os

class StreamArray:
    def __init__(self,path):
        self.file=path.open('x',encoding='utf-8',newline='\n');self.file.write('[');self.count=0
    def append(self,value):
        if self.count:self.file.write(',')
        self.file.write(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False));self.count+=1
    def __len__(self):return self.count
    def close(self):
        if not self.file.closed:
            self.file.write(']\n');self.file.flush();os.fsync(self.file.fileno());self.file.close()

def iter_array(path):
    # Incremental standard-library JSON decode, bounded to one evidence record.
    decoder=json.JSONDecoder();buffer='';pos=0;ended=False
    with path.open(encoding='utf-8-sig') as f:
        while True:
            chunk=f.read(65536)
            if not chunk:
                if not ended:raise ValueError('TRUNCATED_PHYSICAL_ARRAY')
                break
            buffer=buffer[pos:]+chunk;pos=0
            while pos<len(buffer):
                while pos<len(buffer) and buffer[pos] in ' \r\n\t[,':pos+=1
                if pos==len(buffer):break
                if buffer[pos]==']':ended=True;pos+=1;break
                try:value,end=decoder.raw_decode(buffer,pos)
                except json.JSONDecodeError:break
                yield value;pos=end
            if len(buffer)-pos>4000000:raise ValueError('PHYSICAL_RECORD_EXCEEDS_BOUND')

class FileArray:
    def __init__(self,path,count):self.path=path;self.count=count
    def __iter__(self):return iter_array(self.path)
    def __len__(self):return self.count
