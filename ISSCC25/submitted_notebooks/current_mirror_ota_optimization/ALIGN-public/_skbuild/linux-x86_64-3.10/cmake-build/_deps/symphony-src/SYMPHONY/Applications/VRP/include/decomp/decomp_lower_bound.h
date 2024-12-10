#ifndef _DECOMP_LOWER_BOUND_H
#define _DECOMP_LOWER_BOUND_H

#include "sym_proto.h"
#include "cg_user.h"

struct DBL_NEIGHBOR;
struct DBL_EDGE_DATA;

double decomp_lower_bound PROTO((cg_vrp_spec *vrp, double *edge_costs,
				 int *x, int adjust, int mult));
double decomp_make_k_tree PROTO((cg_vrp_spec *vrp, double *edge_costs,
				 int *tree, int k));
int decomp_closest PROTO((struct DBL_NEIGHBOR *nbtree, int *intree, int *last,
			  int *host));
void decomp_insert_edges PROTO((cg_vrp_spec *vrp, double *edge_costs,
				int new_node, struct DBL_NEIGHBOR *nbtree,
				int *intree, int *last, int mu));
int decomp_new_lamda PROTO((cg_vrp_spec *vrp, int upper_bound, int cur_bound,
			    int *lamda, int numroutes, int *tree,
			    struct DBL_EDGE_DATA *cur_edges, int alpha));

#endif
