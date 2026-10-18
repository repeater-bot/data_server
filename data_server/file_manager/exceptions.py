class DirectoryNotEmptyError(Exception):
    """Raised when a non-empty directory is deleted without recursion."""
