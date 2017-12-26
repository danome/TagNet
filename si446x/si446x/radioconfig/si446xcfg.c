#define norace
#include <stdint.h>
#define RPI_BUILD
#include "RadioConfig.h"

#include <Python.h>

static PyObject *get_config_wds(PyObject *self, PyObject *args)
{
  int    c_index, s_len;
  const uint8_t  *s;
  if (!PyArg_ParseTuple(args, "i", &c_index)) {
    return NULL;
  }
  s_len = si446x_wds_config[c_index];
  if (s_len > 16) {
    return NULL;
  }
  c_index += 1;
  s = &si446x_wds_config[c_index];
  return Py_BuildValue("s#", s, s_len);
};

static PyObject *get_config_device(PyObject *self, PyObject *args)
{
  int    c_index, s_len;
  const uint8_t  *s;
  if (!PyArg_ParseTuple(args, "i", &c_index)) {
    return NULL;
  }
  s_len = si446x_device_config[c_index];
  if (s_len > 16) {
    return NULL;
  }
  c_index += 1;
  s = &si446x_device_config[c_index];
  return Py_BuildValue("s#", s, s_len);
};

static PyMethodDef Si446xCfgMethods[] = {
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
