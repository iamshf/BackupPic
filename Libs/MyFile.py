import hashlib, os, datetime,time


def file_hash(file_path, hash_method='sha256'):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} 不存在")
    hash_func = getattr(hashlib, hash_method)()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def file_time(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} 不存在")

    creation_time = os.path.getctime(file_path)
    return time.ctime(creation_time)
    #return creation_time


def scan(path):
    for entry in os.scandir(path):
        if entry.is_file():
            print("filename=",entry.path,",filehash=",file_hash(entry.path),",filetime=",file_time(entry.path));
        else:
            scan(entry.path)



# 使用示例

file = r'd:/software/Clash.Verge_2.5.1_x64-setup.exe'

#print(file_hash(file, 'md5'))
#print(file_hash(file))

print(file_time(file))

scan("d:/software")
