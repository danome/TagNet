si446xcfg.so: Si446xConfigDevice.h si446x.h Si446xRadio.h Si446xWDS_4464_30_434_2GFSK_10_20.h RadioConfig.h Si446xConfigPlatform.h
	gcc -o si446xcfg.so -shared -fPIC -I/usr/include/python2.7 -lpython2.7 si446xcfg.c
	cp si446xcfg.so ..

clean:
	rm si446xcfg.so ../si446xcfg.so
