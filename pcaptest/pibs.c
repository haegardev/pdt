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

#include <hiredis/hiredis.h>

//TODO test other values
#define NBINS 1024

typedef struct pibs_s {
    int errno;
    char *filename;
    //TODO use self contained data structure that can be easily serialized
    uint8_t bins[NBINS];
} pibs_t;

void process_frame(pibs_t* pibs, const struct wtap_pkthdr *phdr,
                   uint_fast8_t *buf, size_t length)
{
    struct ip* ipv4;
    uint32_t x;
    if (length < sizeof(struct ip)) {
        return;
    }
    ipv4 =  (struct ip*)buf;
    memcpy(&x, &ipv4->ip_src, 4);
    pibs->bins[x % NBINS]++;
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

void init(void)
{
    /* Update the start time */
    wtap_init();

}

void pibs_dump(pibs_t* pibs)
{
    int i;
    for (i=0; i< NBINS; i++) {
        printf("%d %d\n",i,pibs->bins[i]);
    }
}

int main(int argc, char* argv[])
{

    int opt;
    pibs_t *pibs;

    pibs=calloc(sizeof(pibs_t),1);
    init();

    fprintf(stderr, "[INFO] pid = %d\n",(int)getpid());

    while ((opt = getopt(argc, argv, "r:")) != -1) {
        switch (opt) {
            case 'r':
                printf("Read pcap file\n");
                process_file(pibs, optarg);
                pibs_dump(pibs);
                break;
            default: /* '?' */
                fprintf(stderr, "[ERROR] Invalid command line was specified\n");
        }
    }

    return EXIT_FAILURE;
}
