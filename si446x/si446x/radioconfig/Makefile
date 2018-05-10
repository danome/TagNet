# Makefile template for shared library

CC = gcc
CFLAGS = -fPIC -Wall -Wextra -O2 -g # C flags
LDFLAGS = -shared
RM = rm -f
TARGET_LIB = si446xcfg.so
WDS = $(wildcard WDS-files/*.c)

SRCS = si446xcfg.c wds_configs.c $(WDS)
INCS = -I/usr/include/python2.7 -lpython2.7 -I./WDS-files
OBJS = $(SRCS:.c=.o)

.PHONY: all
all: ${TARGET_LIB}

$(TARGET_LIB): $(SRCS)
	$(CC) ${CFLAGS} ${LDFLAGS} ${INCS} -o $@ $^
	cp $(TARGET_LIB) ..

.PHONY: clean
clean:
	-${RM} ${TARGET_LIB} ${OBJS}


#
#si446xcfg.so: si446xcfg.c
#	gcc -o si446xcfg.so -shared -fPIC -I/usr/include/python2.7 -lpython2.7 -I./WDS-files si446xcfg.c
#	cp si446xcfg.so ..

#clean:
#	rm si446xcfg.so ../si446xcfg.so
#
# depend:
#	makedepend -o.so si446xcfg.c

#si446xcfg.so: Si446xConfigDevice.h si446x.h Si446xRadio.h Si446xWDS_4463_434_10kb.h RadioConfig.h
#si446xcfg.so: Si446xConfigDevice.h si446x.h Si446xRadio.h RadioConfig.h
#si446xcfg.so: Si446xConfigPlatform.h Si446xConfigWDS.h
