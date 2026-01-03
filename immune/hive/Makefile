#
# SENTINEL IMMUNE — Hive Makefile (Pure BSD)
#

CC=cc
CFLAGS=-Wall -Wextra -O2 -I./include -I/usr/local/include -pthread
LDFLAGS=-L/usr/local/lib -lpthread -lssl -lcrypto

all: dirs objs link

dirs:
	mkdir -p bin obj

objs:
	$(CC) $(CFLAGS) -c src/main.c -o obj/main.o
	$(CC) $(CFLAGS) -c src/hive.c -o obj/hive.o
	$(CC) $(CFLAGS) -c src/network.c -o obj/network.o
	$(CC) $(CFLAGS) -c src/api.c -o obj/api.o
	$(CC) $(CFLAGS) -c src/config.c -o obj/config.o
	$(CC) $(CFLAGS) -c src/herd.c -o obj/herd.o
	$(CC) $(CFLAGS) -c src/alert.c -o obj/alert.o
	$(CC) $(CFLAGS) -c src/scheduler.c -o obj/scheduler.o
	$(CC) $(CFLAGS) -c src/crypto.c -o obj/crypto.o
	$(CC) $(CFLAGS) -c src/forensics.c -o obj/forensics.o
	$(CC) $(CFLAGS) -c src/quarantine.c -o obj/quarantine.o
	$(CC) $(CFLAGS) -c src/response.c -o obj/response.o
	$(CC) $(CFLAGS) -c src/bridge.c -o obj/bridge.o
	$(CC) $(CFLAGS) -c src/deploy.c -o obj/deploy.o
	$(CC) $(CFLAGS) -c src/destruct.c -o obj/destruct.o
	$(CC) $(CFLAGS) -c src/discovery.c -o obj/discovery.o
	$(CC) $(CFLAGS) -c src/exploit.c -o obj/exploit.o
	$(CC) $(CFLAGS) -c src/hammer2.c -o obj/hammer2.o
	$(CC) $(CFLAGS) -c src/hsm.c -o obj/hsm.o
	$(CC) $(CFLAGS) -c src/jail.c -o obj/jail.o
	$(CC) $(CFLAGS) -c src/soc.c -o obj/soc.o

link:
	$(CC) $(CFLAGS) -o bin/hived obj/*.o $(LDFLAGS)
	@echo "Built: bin/hived"

clean:
	rm -rf obj bin
