/*
 * Stupid data structure tests in array to be not used as full of erros.
 * Lists are implemented in an array that can be shared  or serialized easily
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define MAX_ITEMS 3

typedef struct entry_s {
    uint32_t value;
    uint32_t previous;
    uint32_t next;
} entry_t;

typedef struct list_s {
    uint32_t max;
    uint32_t next;
    entry_t* entries;

} list_t;


list_t* list_init(uint32_t max_items) {
    list_t* out;
    printf("sizeof %ld\n", sizeof(list_t));
    out = calloc(sizeof(list_t),1);
    if (out) {
        out->max = max_items;
        out->entries = calloc(sizeof(entry_t), max_items);
        if (out->entries)
            return out;
    } else {
        free(out);
    }
    return NULL;
}

int list_append(list_t* list, uint32_t value)
{
    uint32_t p;
    p = list->next;
    if (list->max >  list->next) {
        list->next++;
        list->entries[list->next].value = value;
        list->entries[list->next].previous = p;
        list->entries[list->next].next = 0;
        list->entries[p].next = list->next;
        printf("Insert value: %d\n", value);
        printf("list->next: %d\n", list->next);
        printf("entry.previous: %d\n", list->entries[list->next].previous);
        printf("entry.next: %d\n", list->entries[list->next].next);
        printf("list->max: %d\n", list->max);
        return EXIT_SUCCESS;
    }
    fprintf(stderr, "list is full\n");
    return EXIT_FAILURE;
}


void list_dump(list_t* list)
{
    uint32_t p;
    p = 0;
    do {
        p = list->entries[p].next;
        if (p) {
            printf("list->entries[p].value %d\n", list->entries[p].value);
        }
    } while (p != 0);
}
int main(int argc, char* argv[])
{
    list_t* list;
    list = list_init(MAX_ITEMS);
    list_append(list, 3);
    list_append(list,2);
    list_append(list,5);

    printf("Dump list\n");
    list_dump(list);
    return EXIT_SUCCESS;
}
