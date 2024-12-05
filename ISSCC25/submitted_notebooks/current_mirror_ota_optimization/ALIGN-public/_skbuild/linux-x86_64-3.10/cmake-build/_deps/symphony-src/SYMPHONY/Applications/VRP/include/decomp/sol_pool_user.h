#ifndef _SOL_POOL_USER_H
#define _SOL_POOL_USER_H

#include "sol_pool.h"
#include "vrp_const.h"

typedef struct VRP_SPEC_SP{
   int vertnum;         /*number of vertices in the problem*/
   int edgenum;         /*number of edges in the problem*/
   int *edges;          /*a list of the edges (by index pairs)*/
}vrp_spec_sp;

int origind_compar PROTO((const void *origind1, const void *origind2));

#endif

