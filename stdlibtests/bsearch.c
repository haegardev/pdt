//Personal trial and errors of stdlib bsearch/qsearch functions
//TODO test tsearch

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>

#define INDEX_SIZE 100

typedef struct bin_s {
    uint32_t number;
    uint32_t offset;
} bin_t;

int cmp(const void *p1, const void *p2)
{
    const bin_t *bin1;
    const bin_t *bin2;

    bin1 = p1;
    bin2 = p2;
    //Must be sorted in descending order?
    return bin2->number > bin1->number;
}

void fill_junk(bin_t* data)
{
    uint32_t i;
    for (i=0; i<INDEX_SIZE; i++) {
        data[i].offset = i;
        data[i].number=random();
    }
}

int dump(bin_t* data)
{
    uint32_t i;
    for (i=0; i < INDEX_SIZE; i++ ) {
        printf("%d -> %d\n",data[i].number,data[i].offset);
    }
    return EXIT_SUCCESS;
}

int main(int argc, char* argv[])
{
    bin_t* data;
    int data_size;
    bin_t key;
    bin_t* res;

    data_size = sizeof(bin_t) * INDEX_SIZE;


    data = calloc(1,data_size);

    assert(data);

    printf("Bin size (bytes): %ld\n", sizeof(bin_t));
    printf("Data size (bytes): %d\n", data_size);

    fill_junk(data);

    data[66].number = 556666;
    data[66].offset = 333;

    qsort(data, INDEX_SIZE, sizeof(bin_t), cmp);

    dump(data);

    key.offset = 0;
    key.number = 556666;

    printf("Searching number %d\n", key.number);
    res = bsearch(&key, data, INDEX_SIZE,sizeof(bin_t),cmp);

    if (res == NULL) {
        printf("Number not found :%d\n", key.number);
    } else {
        printf("Number %d found. Offset = %d\n",res->number, res->offset);
    }
    return EXIT_SUCCESS;
}
