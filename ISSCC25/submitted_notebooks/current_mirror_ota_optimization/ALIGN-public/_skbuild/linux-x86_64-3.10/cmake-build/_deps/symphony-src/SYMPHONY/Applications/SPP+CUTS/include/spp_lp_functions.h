/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2013 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _SPP_LP_FUNCTIONS_H
#define _SPP_LP_FUNCTIONS_H

#include "sym_proto.h"

#include "spp.h"

void spp_init_lp PROTO((spp_lp_problem *spp));
void spp_free_lp_tmp PROTO((spp_lp_problem *spp));
void disp_where_cut_is_from PROTO((int from));
void display_cut_in_lp PROTO((spp_lp_problem *spp, cut_data *cut,
			      double violation));
void cut_to_row PROTO((spp_lp_problem *spp, int n, var_desc **vars,
		       cut_data *cut, int *pnzcnt, int **pmatind,
		       double **pmatval));
void lift_cut_in_lp PROTO((spp_lp_problem *spp, int from, int n,
			   var_desc **vars, cut_data **cut,
			   int *plifted_cutnum, cut_data ***plifted_cuts));
int extend_clique_greedily PROTO((col_ordered *cmatrix, int cl_length,
				  int *cl_indices, int length, int *indices));
char lift_clique PROTO((spp_lp_problem *spp, int n, var_desc **vars,
			double *dj, double dj_threshold, cut_data *cut,
			cut_data *new_cut, int strategy));

#endif
