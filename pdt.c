#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <stdint.h>

#define LINESZ 4096
#define EMSGSZ 4096

typedef struct pdt {
    uint8_t erno;
    char emsg [EMSGSZ];
    //TODO add other generic stuff here
} pdt_t;

void* xalloc(pdt_t* pdt, size_t nmemb, size_t size)
{
    void *ret;
    //TODO put pages in a list
    ret = calloc(nmemb, size);
    if (ret == NULL) {
        //FIXME do something more useful here
        abort();
    }
    return ret;
}

void parse_line_record(pdt_t* pdt, char* line, ssize_t nread)
{
    fwrite(line,nread,1,stdout);
}

void read_text_profile(pdt_t* pdt, char* filename)
{
    FILE* stream = NULL;
    char* line = NULL;
    ssize_t nread;
    size_t len = 0;
    stream = fopen(filename,"r");

    //Reuse same buffer
    line = xalloc(pdt, LINESZ,1);

    if (stream) {
        while ((nread = getline(&line, &len, stream)) != -1){
            parse_line_record(pdt, line, nread);
        }
    }
    free(line);
}

void show_help(pdt_t* pdt)
{
}

int main(int argc, char* argv[])
{
    const char* const short_options = "hr:";
    const struct option long_options[] = {
        { "help",0, NULL, 'h'},
        { "read",0, NULL, 'r'},
        { NULL, 0, NULL, 0}
    };
    int next_option;
    pdt_t *pdt;
    pdt = calloc(sizeof(pdt_t),1);
    if (pdt == NULL) {
        return EXIT_FAILURE;
    }

    do {
        next_option = getopt_long(argc, argv, short_options, long_options,NULL);
        switch (next_option) {
            case 'h':
                show_help(pdt);
                break;
            case 'r':
                read_text_profile(pdt, optarg);
            case -1:
                break;
            default:
                return EXIT_FAILURE;
        }
    } while (next_option != -1);
    return EXIT_SUCCESS;
}
