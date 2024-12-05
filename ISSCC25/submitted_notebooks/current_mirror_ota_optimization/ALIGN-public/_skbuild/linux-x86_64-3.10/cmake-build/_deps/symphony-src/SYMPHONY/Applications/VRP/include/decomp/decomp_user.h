#ifndef _DECOMP_USER_H
#define _DECOMP_USER_H

#include "sym_proto.h"
#include "cg_user.h"

int int_compar PROTO((const void *int1, const void *int2));
void add_tour_to_col_set PROTO((cg_prob *p, int *tour, cg_vrp_spec *vrp,
				dcmp_col_set *cols));
char bfm PROTO((cg_prob *p, int cur_node, int *intour, int *tour,
		dcmp_col_set *cols, edge **stack, int position));
char check_cut PROTO((cg_prob *p, cg_vrp_spec *vrp, cut_data *cut));

#endif


