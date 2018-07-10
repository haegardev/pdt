/*
* pcapdj - dispatch pcap files
*
* Copyright (C) 2013 Gerard Wagener
* Copyright (C) 2013 CIRCL Computer Incident Response Center Luxembourg 
* (SMILE gie).
*
* This program is free software: you can redistribute it and/or modify
* it under the terms of the GNU Affero General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU Affero General Public License for more details.
*
* You should have received a copy of the GNU Affero General Public License
* along with this program. If not, see <http://www.gnu.org/licenses/>.
*/
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <assert.h>
#include <string.h>
#include <pcap/pcap.h>
#include <wtap.h>
#include <unistd.h>
#include <signal.h>
#include <netinet/ip.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <hiredis/hiredis.h>

//TODO test other values
#define NBINS 1024 //Number of bins
#define NBINITEMS 255 //Number of items per bin
#define SZBIN 4
#define NBINSCALE 2 // Scaling factor of the entire datastructure

#define HDBG(...) if (HASHDEBUG) fprintf(stderr, __VA_ARGS__)

typedef struct pibs_header_s {
    uint8_t magic [4];
    uint8_t version;
    //Put some useful stuff here
    uint8_t padding [3];
} pibs_header_t;


/* TODO This can squezed. Timestamp can be expressed on 8 bits i.e. relative
 * minutes
 * IP can be represented with 16 bits ipaddr = ip / bin_size
 * Not sure if space can be saved in usual cases
 */
typedef struct item_s {
    uint32_t timestamp;
    uint8_t tcp_flags;
    uint32_t next_item;
    uint32_t ipaddr;
} item_t;

/* Need to hash source IP addresses and record first seen and flags */
typedef struct pibs_s {
    int errno;
    char *filename;
    //TODO use self contained data structure that can be easily serialized
    //Put data structure in an entire block to easier serialize
    uint8_t *data;
    uint32_t next_block;
    uint32_t next_item;
    uint32_t bin_offset;
    uint64_t data_size;
    uint32_t* bin_table;
    item_t* items;
} pibs_t;

/*
 * Returns -1 if not found
 * returns last timestamp if found
 */
int_fast64_t get_last_timestamp(pibs_t* pibs, uint32_t ip)
{
    uint32_t idx;
    uint32_t i;

    idx = ip % NBINS;
    HDBG("[TS] Checking for IP %x at index = %d\n", ip, idx);
    i = pibs->bin_table[idx];
    if (i){
        do {
            if (pibs->items[i].ipaddr == ip) {
                HDBG("[TS] Found item %x at position %d\n", ip , i);
                return pibs->items[i].timestamp;
            }
            i = pibs->items[i].next_item;
        } while (pibs->items[i].next_item !=0);
    }
    HDBG("[TS] IP: %x was not found return -1\n",ip);
    return -1;
}

void insert_ip(pibs_t* pibs, uint32_t ip, uint32_t ts)
{
    uint32_t idx;
    uint32_t i;
    uint8_t found;

    idx = ip  % NBINS;
    HDBG("[INS] Lookup IP address %x. Hashed value: %d\n", ip, idx);
    if (!pibs->bin_table[idx]) {
        pibs->next_item++;
        HDBG("[INS] Observed first time %x. Created new item at position %d\n",ip,\
                pibs->next_item);
        // FIXME check size
        pibs->bin_table[idx] = pibs->next_item;
        pibs->items[pibs->next_item].ipaddr = ip;
        pibs->items[pibs->next_item].timestamp = ts;
        HDBG("[INS] Address of IP %p\n", &(pibs->items[idx].ipaddr));
        HDBG("[INS] Next item %d\n",pibs->items[idx].next_item);
        return;
    }
    found = 0;
    i = pibs->bin_table[idx];
    HDBG("[INS] Starting searching at position %d\n", i);

    do {
        HDBG("[INS] Iterating items at index %d. Current position: %d. Next position = %d\n",
               idx,i,pibs->items[i].next_item);
        HDBG("[INS] Checking IP at address %p\n",&pibs->items[i]);
        if (pibs->items[i].ipaddr == ip) {
            HDBG("[INS] Found item %x at position %d\n", ip , i);
            found = 1;
            break;
        }
        i = pibs->items[i].next_item;
    } while (pibs->items[i].next_item !=0);

    //Insert new item if not found
    if (!found) {
        pibs->next_item++;
        HDBG("[INS] Insert new item %d at %d\n", pibs->next_item, i);
        pibs->items[i].next_item = pibs->next_item;
        pibs->items[i].ipaddr = ip;
        pibs->items[i].timestamp = ts;
    }
}

void process_frame(pibs_t* pibs, const struct wtap_pkthdr *phdr,
                   uint8_t *buf, size_t length)
{
    struct ip* ipv4;
    uint32_t ip;
    struct tcphdr* tcp;
    int_fast64_t lastseen;

    if (length < sizeof(struct ip)) {
        return;
    }


    ipv4 =  (struct ip*)buf;
    // Focus only on TCP packets
    if (ipv4->ip_p != 6)
        return;

    tcp = (struct tcphdr*)(buf+sizeof(struct ip));

    memcpy(&ip, &ipv4->ip_src, 4);
    // Record only source ips where syn flag is set
    // TODO check other connection establishment alternatives
    if (tcp->th_flags  == 2 ){
        insert_ip(pibs, ip, phdr->ts.secs);
        return;
    }

    lastseen =  get_last_timestamp(pibs, ip);

    if (lastseen > 0){
        HDBG("IP %x %s was already seen before at %ld. Time difference %ld.\n"
               , ip, inet_ntoa(ipv4->ip_src), lastseen, phdr->ts.secs-lastseen);
        return;
    }
    // TODO keep these IPs in a hashtable and rank them
    printf("Potential backscatter. IP. %s. TCP flags: %d. Source port:%d \n",
           inet_ntoa(ipv4->ip_src), tcp->th_flags, ntohs(tcp->th_sport));
    //TODO relative time
    //Purge old ips?
}

void process_file(pibs_t* pibs, char* filename)
{
    wtap *wth;
    int err;
    char *errinfo;
    gint64 data_offset;
    const struct wtap_pkthdr *phdr;
    int ethertype;
    guint8 *buf;

    fprintf(stderr,"Processing %s\n",filename);
    wth = wtap_open_offline ( filename, WTAP_TYPE_AUTO, (int*)&err,
                             (char**)&errinfo, FALSE);
    if (wth) {
        /* Loop over the packets and adjust the headers */
        while (wtap_read(wth, &err, &errinfo, &data_offset)) {
            phdr = wtap_phdr(wth);
            buf = wtap_buf_ptr(wth);
            if (phdr->caplen < 14) {
                fprintf(stderr,"Packet too small, skip\n");
                continue;
            }
            ethertype = buf[12] << 8 | buf[13];
            // TODO Focus on IPv4 only
            if (ethertype == 0x0800) {
                process_frame(pibs, phdr,buf+14, phdr->caplen-14);
            }
        }
        wtap_close(wth);
	fprintf(stderr,"[INFO] Processing of filename %s done\n",filename);
    }else{
        fprintf(stderr, "[ERROR] Could not open filename %s,cause=%s\n",filename,
                wtap_strerror(err));
    }
}

pibs_t* init(void)
{
    pibs_t *pibs;

    wtap_init();
    pibs=calloc(sizeof(pibs_t),1);
    pibs->data_size = sizeof(pibs_header_t) + NBINSCALE * NBINS * SZBIN * NBINITEMS * sizeof(item_t);
    pibs->data = calloc(pibs->data_size,1);
    printf("Internal look up structure size in bytes: %ld\n",  pibs->data_size);
    // Build header
    pibs->data[0]='P';
    pibs->data[1] = 'I';
    pibs->data[2] = 'B';
    pibs->data[3] = 'S';
    pibs->data[4] = 1; //version 1
    pibs->next_block = sizeof(pibs_header_t);
    pibs->bin_offset = pibs->next_block;
    printf("data address is %p\n",pibs->data);
    pibs->bin_table = (uint32_t*)(pibs->data+pibs->bin_offset);
    printf("bin_table address is %p\n", pibs->bin_table);
    // Create bins
    pibs->next_block+=SZBIN * NBINS;
    printf("Next block %d\n", pibs->next_block);
    pibs->items = (item_t*)(pibs->data+pibs->next_block);
    pibs->next_item = 0;
    printf("items are address %p\n", pibs->items);
    return pibs;
}

void pibs_dump_raw(pibs_t* pibs)
{
    int i;
    printf("#RAW table dump\n");
    printf("#Index next_item\n");
    printf("#BINs\n");
    for (i=0; i< NBINS; i++) {
        printf("%d  %d\n", i, pibs->bin_table[i]);
    }
    printf("#ITEMS\n");
    printf("#Index next_item, timestamp, ipaddr\n");
    for (i=0; i < NBINITEMS * NBINS; i++) {
        printf("%d %d %d %x\n", i, pibs->items[i].next_item,
                                 pibs->items[i].timestamp,
                                 pibs->items[i].ipaddr);
    }
}

void pibs_dump(pibs_t* pibs)
{
    int i;
    int j;
    int cnt;
    uint64_t sum;
    sum = 0;
    printf("#Bin table\n");
    printf("#Bin number, Item offset, number of items\n");
    for (i=0; i < NBINS; i++) {
        j = pibs->items[pibs->bin_table[i]].next_item;
        cnt = 0;
        while (j) {
            cnt++;
            j=pibs->items[j].next_item;
        }
        sum+=cnt;
        printf("%d %d %d\n", i, pibs->bin_table[i], cnt);
    }
    printf("#Number of unique IP addresses: %ld\n", sum);
}

int main(int argc, char* argv[])
{

    int opt;
    pibs_t* pibs;

    pibs  = init();

    fprintf(stderr, "[INFO] pid = %d\n",(int)getpid());

    while ((opt = getopt(argc, argv, "r:")) != -1) {
        switch (opt) {
            case 'r':
                printf("Read pcap file\n");
                process_file(pibs, optarg);
                pibs_dump_raw(pibs);
                break;
            default: /* '?' */
                fprintf(stderr, "[ERROR] Invalid command line was specified\n");
        }
    }

    return EXIT_FAILURE;
}
