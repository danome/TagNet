si446xcfg.so: si446xcfg.c
	gcc -o si446xcfg.so -shared -fPIC -I/usr/include/python2.7 -lpython2.7 si446xcfg.c
	cp si446xcfg.so ..

clean:
	rm si446xcfg.so ../si446xcfg.so

# depend:
#	makedepend -o.so si446xcfg.c

#si446xcfg.so: Si446xConfigDevice.h si446x.h Si446xRadio.h Si446xWDS_4463_434_10kb.h RadioConfig.h
si446xcfg.so: Si446xConfigDevice.h si446x.h Si446xRadio.h RadioConfig.h
si446xcfg.so: Si446xConfigPlatform.h Si446xConfigWDS.h
