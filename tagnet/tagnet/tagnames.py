import os, sys, types
from os.path import normpath, commonprefix

from tagdef import *
from tagtlv import *


class TagName(TlvList):
    """
    constructor for tag names, which consist of a list of tag tlv's that represent the hierachical order of
    name components as defined by the list.
    """    
    def __init__(self, *args, **kwargs):
        """
        New object can be initailized with following types:
            - string     = url formatted string, parsed into sequence of string tlv type/values
            - TagName    = from an existing TagName object
            - packet     = a byte sequence representing a protocol packet containing a name
            - tuple list = list of tuples to initialize TagName tlv type/values, same as TagName
            - empty list = new TagName object with no tlv items
        """
        super(TagName,self).__init__(*args, **kwargs)

    def copy(self):
        """
        make an exact copy of this name in a new list object
        """
        return TagName(self)



#------------ end of class definition ---------------------

def test():
    v1 = TagName('tgn://foo/bar')
    v2 = TagName(v1)
    v3 = v1.copy()
    v3.append((tlv_types.STRING, 'baz'))

    if (v1 != v2): print('compare error: ',v1,v2)
    if (v1 == v3): print('compare error: ',v1,v3)
    if (not v3.startswith(v1)): print('startswith error: ',v3,v1)
    if (v1.startswith(v3)): print('startswith error: ',v1,v3)
    return (v1,v2,v3)
    
if __name__ == '__main__':
    test()
