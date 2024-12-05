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

#ifndef _SPP_CG_FUNCTIONS_H
#define _SPP_CG_FUNCTIONS_H

int find_violated_odd_holes PROTO((spp_cg_problem *spp, double etol));
double find_chordless_oh PROTO((spp_cg_problem *spp, frac_graph *fgraph,
				int u, int w, int *oh));
void min_path_to_root PROTO((spp_cg_problem *spp, frac_graph *fgraph,
			     int u, int *path_u, double *pcost));
double lift_nonviolated_odd_hole PROTO((spp_cg_problem *spp, int oh_len,
					int *oh, double lhs_oh, int *phub_len,
					int *hubs, int *hub_coef));
int max_lhs_of_lifted_odd_hole PROTO((spp_cg_problem *spp, int oh_len,
				      int *oh, int hub, int hub_len, int *hubs,
				      int *hub_coef, char *label, int pos));
int find_violated_odd_antiholes PROTO((spp_cg_problem *spp, double etol));
double lift_nonviolated_odd_antihole PROTO((spp_cg_problem *spp, int oah_len,
					    int *oah, double lhs_oah,
					    int *phub_len, int *hubs,
					    int *hub_coef, double etol));
void translate_cut_to_indices PROTO((spp_cg_problem *spp, cut_data *cut));
void rotate_odd_hole PROTO((int length, int *indices, int *itmp));

#endif
