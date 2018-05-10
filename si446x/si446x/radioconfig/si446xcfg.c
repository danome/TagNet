#include <stdint.h>

// don't need this attribute for the RPi C compiler
#define norace

// need this name to allow differences between RPi and Tag code
#define RPI_BUILD

#include "RadioConfig.h"

#include <Python.h>

const uint8_t const * const *wds_config_list();
uint8_t const *wds_config_select(uint8_t *cname);


#define MAX_CFG_STRINGS 1000

int count_strings(uint8_t * pstrs) {
  int            count = 0;
  int            x;

  for (x = 0; x < MAX_CFG_STRINGS;) {
    if (pstrs[x] == 0) break;
    x += pstrs[x] + 1;
    count += 1;
  }
  return count;
}

int sum_strings(uint8_t * pstrs) {
  int            x;

  for (x = 0; x < MAX_CFG_STRINGS;) {
    if (pstrs[x] == 0) break;
    x += pstrs[x] + 1;
  }
  return x;
}

static PyObject *wds_config_count(__attribute__((unused)) PyObject *self, __attribute__((unused)) PyObject *args) {
  uint8_t *cfg_str;

  cfg_str = (uint8_t *) wds_config_select(NULL);
  return Py_BuildValue("(ii)", count_strings(cfg_str),
                       sum_strings(cfg_str));
}

static PyObject *wds_config_str(__attribute__((unused)) PyObject *self, __attribute__((unused)) PyObject *args) {
  uint8_t *cfg_str;

  cfg_str = (uint8_t *) wds_config_select(NULL);
  return Py_BuildValue("(s#)", cfg_str, sum_strings(cfg_str));
#ifdef notdef
  int            count = 0;
  const uint8_t *cfg_str, *s;
  int            x;
  PyObject      *cfg_lst;

  cfg_str = (uint8_t *) wds_config_select(NULL);
  count = count_strings((uint8_t *) cfg_str);
  cfg_lst = PyList_New(count);
  for (x = 0; x < count;) {
    PyList_SET_ITEM(cfg_lst, x, PyString_FromStringAndSize((const char *)&cfg_str[x+1], cfg_str[x]));
    x += cfg_str[x] + 1;
  }
  return cfg_lst;
#endif
}

static PyObject *get_name_wds(__attribute__((unused)) PyObject *self, __attribute__((unused)) PyObject *args) {
  const uint8_t  *s = wds_config_list()[1];

  return Py_BuildValue("s", s);
};

static PyObject *get_config_wds(__attribute__((unused)) PyObject *self, PyObject *args) {
  int    c_index, s_len;
  const uint8_t  *s;
  uint8_t *cfg_str;

  cfg_str = (uint8_t *) wds_config_select(NULL);

  if (!PyArg_ParseTuple(args, "i", &c_index)) {
    return NULL;
  }
  s_len = cfg_str[c_index];
  if (s_len > 16) {
    return NULL;
  }
  c_index += 1;
  s = &cfg_str[c_index];
  return Py_BuildValue("s#", s, s_len);
};

static PyObject *get_config_device(__attribute__((unused)) PyObject *self, PyObject *args)
{
  int    c_index, s_len;
  const uint8_t  *s;
  uint8_t *cfg_str;

  cfg_str = (uint8_t *) si446x_device_config;

  if (!PyArg_ParseTuple(args, "i", &c_index)) {
    return NULL;
  }
  s_len = cfg_str[c_index];
  if (s_len > 16) {
    return NULL;
  }
  c_index += 1;
  s = &cfg_str[c_index];
  return Py_BuildValue("s#", s, s_len);
};

static PyMethodDef Si446xCfgMethods[] = {
  {"wds_config_count", wds_config_count, METH_VARARGS,
   "returns number of strings in configuration"},
  {"wds_config_str", wds_config_str, METH_VARARGS,
   "returns wds configuration as a string"},
  {"get_name_wds", get_name_wds, METH_VARARGS,
   "get name of WDS source file"},
  {"get_config_wds", get_config_wds, METH_VARARGS,
   "get next string from WDS config string array at index offset"},
  {"get_config_device", get_config_device, METH_VARARGS,
   "get next string from device config string array at index offset"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initsi446xcfg(void)
{
  (void) Py_InitModule("si446xcfg", Si446xCfgMethods);
}
