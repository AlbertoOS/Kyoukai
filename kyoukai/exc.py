"""
Kyokai exceptions.
"""


class HTTPException(Exception):
    """
    A basic HTTP error.

    Should not be created directly, only caught, or one of the subclasses caught.
    """
    def __init__(self, errcode, msg=None,
                 route=None):
        self.code = errcode

        self.msg = None

        self.route = route

    def __repr__(self):
        # TODO: Add a lookup.
        return "HTTP {} {}".format(self.code, self.msg)
