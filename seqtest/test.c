// Sequential iteration over array for comparing performance
//with SQLtest
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <getopt.h>
#define NRECORDS 8000000
//Takes 254MB on disk
//Query time < 1s

typedef struct record_s {
    uint32_t ts;
    uint32_t sip;
    uint16_t sp;
    uint32_t dip;
    uint16_t dp;
    uint8_t proto;
    uint8_t ttl;
    uint32_t seq;
    uint32_t ack;
    uint8_t flag;
} record_t;

void query(void)
{
    record_t* records;
    int i;
    records = calloc(NRECORDS,sizeof(record_t));
    printf("Data record %ld\n", sizeof(record_t));
    //sequential search with. program execution time < 0.12s
    for (i=0; i < NRECORDS; i++) {
        if ((records[i].sip == 0xabcde) & (records[i].sp > 23) & (records[i].sp < 55)) {
            printf("Query matched\n");
        }
    }
}

// 0.3 s on non ssd drive
void store_data(void)
{
    record_t* records;
    int i;
    FILE* fp;

    records = calloc(NRECORDS,sizeof(record_t));
    fp = fopen("test.dat","w");
    fwrite(records,  NRECORDS*sizeof(record_t),1,fp);
    fclose(fp);
}

void load(void)
{
    record_t* records;
    int i;
    FILE* fp;

    records = calloc(NRECORDS,sizeof(record_t));
    fp = fopen("test.dat","r");
    fread(records,  NRECORDS*sizeof(record_t),1,fp);
    fclose(fp);
    //sequential search with. program execution time < 0.12s
    for (i=0; i < NRECORDS; i++) {
        if ((records[i].sip == 0xabcde) & (records[i].sp > 23) & (records[i].sp < 55)) {
            printf("Query matched\n");
        }
    }
}


int main(int argc, char* argv[])
{
    //store_data();
   load();
   return EXIT_SUCCESS;
}
