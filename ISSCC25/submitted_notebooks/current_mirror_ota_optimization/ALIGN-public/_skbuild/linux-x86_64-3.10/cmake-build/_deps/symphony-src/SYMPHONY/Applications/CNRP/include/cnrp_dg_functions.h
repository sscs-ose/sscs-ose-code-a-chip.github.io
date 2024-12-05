/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2013 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _CNRP_DG_FUNCTIONS_H
#define _CNRP_DG_FUNCTIONS_H

/* SYMPHONY include files */
#include "sym_proto.h"

/* CNRP include files */
#include "cnrp_common_types.h"

void init_window PROTO((int dg_id, char *name, int width, int height));
void wait_for_click PROTO((int dg_id, char *name, int report));
void display_graph PROTO((int dg_id, char *name));
void copy_node_set PROTO((int dg_id, int clone, char *name));
void disp_vrp_tour PROTO((int dg_id, int clone, char *name,
			  _node *tour, int vertnum, int numroutes,int report));
void draw_edge_set_from_edge_data PROTO((int dg_id, char *name,
					 int edgenum, edge_data *edges));
void draw_edge_set_from_userind PROTO((int dg_id, char *name,
				       int edgenum, int *userind));
void draw_weighted_edge_set PROTO((int dg_id, char *name,
				   int edgenum, int *userind,
				   double *value, double etol));
void display_support_graph PROTO((int dg_id, int clone, char *name,
				  int edgenum, int *userind,
				  double *value, double etol,
				  int total_edgenum, int report));
void display_support_graph_flow PROTO((int dg_id, int clone, char *name,
				int edgenum, int flow_start, int *userind,
				double *value, double etol, int total_edgenum,
				       int report));
void display_compressed_support_graph PROTO((int dg_id, int clone, char *name,
					     int edgenum, int *userind,
					     double *value, int report));
void display_part_tour PROTO((int dg_id, int clone, char *name, int *tour,
		       int numroutes, int report));
void delete_graph PROTO((int dg_id, char *name));
void disp_lb PROTO((int dg_id, int clone, char *name, int *tree,
		    struct DBL_EDGE_DATA *best_edges, int vertnum,
		    int numroutes, int report));
#endif
