class OutOfBoundVolumeError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)

class VolumeTypeError(TypeError):
    def __init__(self, needed_type: any, given_type: any) -> None:
        self.needed_type = needed_type
        self.given_type = given_type

        super().__init__(self.needed_type, self.given_type)

    def __str__(self) -> str:
        return "Method needed object of type {0}, but was given {1} instead".format(self.needed_type, self.given_type)

    def __repr__(self) -> str:
        return "Method needed object of type {0}, but was given {1} instead".format(self.needed_type, self.given_type)
