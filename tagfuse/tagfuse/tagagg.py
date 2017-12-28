from collections import OrderedDict
import struct
import os

#__all__=[atom, aggie, get_dir_names, get_meta]

class atom(object):
    '''
    takes 1-tuple: (node_stat)

    set will set the instance.attribute "val" to the obj
    passed in.
    '''
    def __init__(self, meta, action=None):
        self.meta = meta
        self.action = action

    def __len__(self):
        return 1

    def collect_meta(self, path_list):
        return self.meta

class aggie(OrderedDict):
    '''
    aggie: aggregation node.
    takes one parameter a dictionary of key -> {atom | aggie}
    '''
    def __init__(self, a_dict):
        super(aggie, self).__init__(a_dict)

    def __len__(self):
        cnt = 0
        for key, v_obj in self.iteritems():
            if isinstance(v_obj, aggie):
                cnt += len(v_obj)
        return cnt

    def _collect_dir_info(self, path_list):
        dir_names = []
        meta     = None
        if (len(path_list) > 1):
            for key, v_obj in self.iteritems():
                if (path_list[0] == key):
                    if isinstance(v_obj, aggie):
                        dir_names  = v_obj.collect_dir_names(path_list[1:])
                        meta       = v_obj.collect_meta(path_list[1:])
                    break
        else:
            if (not path_list): path_list = ['']
            if path_list[0] == '':
                for key, v_obj in self.iteritems():
#                    print(key, v_obj)
                    if (key != ''):
                        dir_names.append(key)
                    elif isinstance(v_obj, atom):
                        meta = v_obj.collect_meta([''])
#                    print(dir_names,meta)
            else:
                for key, v_obj in self.iteritems():
                    if (path_list[0] == key):
                        if isinstance(v_obj, aggie):
                            dir_names = v_obj.collect_dir_names([''])
                        meta = v_obj.collect_meta([''])
                        break
#        print(dir_names)
#        if (meta): print(meta.attrs)
        return dir_names, meta

    def collect_dir_names(self, path_list):
        return self._collect_dir_info(path_list)[0]

    def collect_meta(self, path_list):
        return self._collect_dir_info(path_list)[1]


def get_dir_names(tree, path):
        path = os.path.abspath(os.path.realpath(path))
#        print('get_dir_names', path)
        names = tree.collect_dir_names(path.split('/')[1:])
#        print('got_dir_names', names)
        return names

def get_meta(tree, path):
        path = os.path.abspath(os.path.realpath(path))
#        print('get_meta', path)
        meta = tree.collect_meta(path.split('/')[1:])
#        print('got_meta', meta)
        return meta
