#ifndef _IND_SORT
#define _IND_SORT

#include "sym_proto.h"

void exchange PROTO((int *ind_list, double *vals, int i, int j));
int partition PROTO((int *ind_list, double *vals, int len));
void ind_sort PROTO((int *ind_list, double *vals, int len));

#endif
