#include <stdint.h>

// don't need this attribute for the RPi C compiler
#define norace

// need this name to allow differences between RPi and Tag code
#define RPI_BUILD

#include "RadioConfig.h"
#include "wds_configs.h"

#include <Python.h>


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
  return Py_BuildValue("s", wds_default_name());
};

static PyObject *get_ids_wds(__attribute__((unused)) PyObject *self, __attribute__((unused)) PyObject *args) {
  const wds_config_ids_t *ids;
  ids = wds_default_ids();
  return Py_BuildValue("{s:i,s:i,s:i,s:i,s:i,s:i}",
                       "sig",       ids->sig,
                       "xtal_freq", ids->xtal_freq,
                       "bps",       ids->symb_sec,
                       "freq_dev",  ids->freq_dev,
                       "fhst",      ids->fhst,
                       "rxbw",      ids->rxbw);
};

static PyObject *wds_default_config(__attribute__((unused)) PyObject *self, PyObject *args) {
  int    c_level;

  if (!PyArg_ParseTuple(args, "i", &c_level)) {
    c_level = -1;
  }
  return Py_BuildValue("i", wds_set_default(c_level));
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
  {"get_ids_wds", get_ids_wds, METH_VARARGS,
   "get name of WDS configuration file identifiers (e.g, bitrate, chrystal frequency)"},
  {"get_config_wds", get_config_wds, METH_VARARGS,
   "get next string from WDS config string array at index offset"},
  {"get_config_device", get_config_device, METH_VARARGS,
   "get next string from device config string array at index offset"},
  {"wds_default_config", wds_default_config, METH_VARARGS,
   "get and optional set the default configuration file"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initsi446xcfg(void)
{
  (void) Py_InitModule("si446xcfg", Si446xCfgMethods);
}
