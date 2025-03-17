#ifndef CJSON_H
#define CJSON_H

#include <stdlib.h>
#include <string.h>

// Define the cJSON structure
typedef struct cJSON {
    struct cJSON *next;
    struct cJSON *prev;
    struct cJSON *child;
    int type;
    char *valuestring;
    int valueint;
    double valuedouble;
    char *string;
} cJSON;

// Function declarations
cJSON *cJSON_Parse(const char *value);
void cJSON_Delete(cJSON *c);
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON *object, const char *string);
int cJSON_IsNumber(const cJSON *item);
int cJSON_IsString(const cJSON *item);

#endif // CJSON_H
