#ifndef _MIN_CUT_H
#define _MIN_CUT_H

#include "sym_proto.h"
#include "cg_user.h"
#include "network.h"

int min_cut PROTO((cg_vrp_spec *vrp, network *n, double etol));
int shrink_one_edges PROTO((cg_vrp_spec *vrp, network *n, int *cur_verts,
			    int *cur_edges, int capacity, double etol));

#endif
