#ifndef _MY_DECOMP_H
#define _MY_DECOMP_H

#include "sym_proto.h"
#include "sym_cg.h"
#include "sym_lp.h"
#include "network.h"
#include "cg_user.h"

#define MAXM 250

int origind_compar PROTO((const void *origind1, const void *origind2));

char bfm PROTO((cg_prob *p, int cur_node, int *intour, int *tour,
		edge **stack, int position,int low_tour_num,
		int high_tour_num ,int cur_comp, double *weight,
		double *weight_uncovered, int *cost));

int vrp_create_initial_lp PROTO((cg_prob *p, network *n, int cur_comp,
				 int num_comps, int *compdemands,
				 edge **row_edges,
				 int *generated_all_columns));
int vrp_decomp PROTO((int comp_num, double *compdensity));
char add_tour_to_col_set PROTO((cg_prob *p, int *tour, cg_vrp_spec *vrp,
				int node_num, network *n ));
void usr_open_decomp_lp PROTO((cg_prob *p, int varnum));
void close_decomp_lp PROTO((cg_prob *p));
int vrp_generate_cuts PROTO((cg_prob *p, network *n, int cur_comp,
			     edge **row_edges, int generate_cuts));
int vrp_check_col PROTO((cg_prob *p, int *colind, double *colval, int collen,
			  network *n, int cur_comp, edge **row_edges));
int generate_farkas_cuts PROTO((cg_prob *p,LPdata *lp_data, network *n,
				edge **row_edges, int comp_num));
int generate_no_cols_cut PROTO((cg_prob *p, LPdata *lp_data, network *n,
				edge **row_edges, int cur_comp));
int purge_infeasible_cols PROTO((cg_prob *p, LPdata *lp_data, edge **row_edges,
				 int *delstat));
int vrp_generate_new_cols PROTO((cg_prob *p, LPdata *lp_data, network *n,
				 edge **row_edges, int comp_num));
#endif
