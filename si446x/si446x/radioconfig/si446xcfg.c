#define norace
#include <stdint.h>
#define SI446X_CHIP  0x4463
#include "si446x.h"
#undef SI446X_CHIP
#include "radio_config_si446x.h"
#include "radio_platform_si446x.h"
#include "si446xLocalConfig.h"


const uint8_t si446x_wds_config[] = SI446X_WDS_CONFIG_BYTES;

const uint8_t si446x_local_config[] = {
     SI446X_GPIO_PIN_CFG_LEN,          SI446X_RF_GPIO_PIN_CFG,
     SI446X_GLOBAL_CONFIG_1_LEN,       SI446X_GLOBAL_CONFIG_1,
     SI446X_INT_CTL_ENABLE_4_LEN,      SI446X_INT_CTL_ENABLE_4,
     SI446X_PREAMBLE_LEN,              SI446X_PREAMBLE,
     SI446X_PKT_CRC_CONFIG_7_LEN,      SI446X_PKT_CRC_CONFIG_7,
     SI446X_PKT_LEN_5_LEN,             SI446X_PKT_LEN_5,
     SI446X_PKT_TX_FIELD_CONFIG_6_LEN, SI446X_PKT_TX_FIELD_CONFIG_6,
     SI446X_PKT_RX_FIELD_CONFIG_10_LEN,SI446X_PKT_RX_FIELD_CONFIG_10,
     SI446X_MODEM_RSSI_LEN,            SI446X_MODEM_RSSI,
0
};

char get_config_wds(int index) {
     char s;
     s = si446x_wds_config[index];
     return s;
}

char get_config_local(int index) {
     char s;
     s = si446x_local_config[index];
     return s;
}

