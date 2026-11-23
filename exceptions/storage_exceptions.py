class StorageError(Exception):
    pass

class RemoteFileExistError(StorageError):
    pass

class TokenRefreshError(StorageError):
    pass
