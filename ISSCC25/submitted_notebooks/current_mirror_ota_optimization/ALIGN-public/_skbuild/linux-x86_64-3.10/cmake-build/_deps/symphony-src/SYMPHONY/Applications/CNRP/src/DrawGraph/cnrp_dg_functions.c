/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_proccomm.h"
#include "sym_dg_params.h"
#include "sym_qsort.h"

/* CNRP include files */
#include "cnrp_messages.h"
#include "cnrp_common_types.h"
#include "cnrp_dg_functions.h"
#include "cnrp_macros.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains additional user functions for the draw graph process.
\*===========================================================================*/

void init_window(int dg_id, char *name, int width, int height)
{
   if (dg_id){
      int s_bufid, code;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      send_str(name);
      /* no change in the default window_desc data structure */
      code = 4;
      send_int_array(&code, 1);
      code = CANVAS_WIDTH;
      send_int_array(&code, 1);
      send_int_array(&width, 1);
      code = CANVAS_HEIGHT;
      send_int_array(&code, 1);
      send_int_array(&height, 1);
      code = VIEWABLE_WIDTH;
      send_int_array(&code, 1);
      send_int_array(&width, 1);
      code = VIEWABLE_HEIGHT;
      send_int_array(&code, 1);
      send_int_array(&height, 1);
      send_msg(dg_id, CTOI_INITIALIZE_WINDOW);
      freebuf(s_bufid);
   }
}

/*===========================================================================*/

void wait_for_click(int dg_id, char *name, int report)
{
   if (dg_id){
      int s_bufid, r_bufid;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      send_msg(dg_id, report);
      freebuf(s_bufid);
      if (report == CTOI_WAIT_FOR_CLICK_AND_REPORT){
	 r_bufid = receive_msg(dg_id, ITOC_CLICK_HAPPENED);
	 freebuf(r_bufid);
      }
   }
}

/*===========================================================================*/

void delete_graph(int dg_id, char *name)
{
   if (dg_id){
      int s_bufid;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      send_msg(dg_id, CTOI_DELETE_GRAPH);
      freebuf(s_bufid);
   }
}

/*===========================================================================*/

void display_graph(int dg_id, char *name)
{
   if (dg_id){
      int s_bufid;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      send_msg(dg_id, CTOI_DRAW_GRAPH);
      freebuf(s_bufid);
   }
}

/*===========================================================================*/

void copy_node_set(int dg_id, int clone, char *name)
{
   if (dg_id){
      int s_bufid;
      char node_place[MAX_NAME_LENGTH +1] = {"node_placement"};
      s_bufid = init_send(DataInPlace);
      if (clone){
	 send_str(node_place);
	 send_str(name);
	 send_str(name);
	 send_msg(dg_id, CTOI_CLONE_WINDOW);
      }else{
	 send_str(name);
	 send_str(node_place);
	 send_msg(dg_id, CTOI_COPY_GRAPH);
      }
      freebuf(s_bufid);
   }
}

/*===========================================================================*/

void disp_vrp_tour(int dg_id, int clone, char *name,
		   _node *tour, int vertnum, int numroutes, int report)
{
   if (dg_id){
      int i, j, prev_j, key = 0, s_bufid, zero = 0;
      int v0 = 0, v1 = tour[0].next;
      int edgenum = vertnum+numroutes-1;

      copy_node_set(dg_id, clone, name);
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      j = INDEX(v0, v1);
      send_int_array(&j, 1);
      send_int_array(&v0, 1);
      send_int_array(&v1, 1);
      send_int_array(&key, 1);
      for (i = 1; i < vertnum; i++){
	 v1=tour[v0=v1].next;
	 if (tour[v0].route == tour[v1].route){
	    j = INDEX(v0, v1);
	    send_int_array(&j, 1);
	    send_int_array(&v0, 1);
	    send_int_array(&v1, 1);
	    send_int_array(&key, 1);
	 }else if (v1 == 0){
	    j = INDEX(v0, 0);
	    send_int_array(&j, 1);
	    send_int_array(&v0, 1);
	    send_int_array(&zero, 1);
	    send_int_array(&key, 1);
	 }else{
	    prev_j = j;
	    if ((j = INDEX(v0, 0)) != prev_j){
	       send_int_array(&j, 1);
	       send_int_array(&v0, 1);
	       send_int_array(&zero, 1);
	       send_int_array(&key, 1);
	    }
	    j = INDEX(0, v1);
	    send_int_array(&j, 1);
	    send_int_array(&zero, 1);
	    send_int_array(&v1, 1);
	    send_int_array(&key, 1);
	 }
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
      display_graph(dg_id, name);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
}

/*===========================================================================*/

void draw_edge_set_from_edge_data(int dg_id, char *name,
				  int edgenum, edge_data *edges)
{
   if (dg_id){
      int i, j, key, s_bufid;

      key = 0;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      for (i = 0; i < edgenum; i++){
	 j = INDEX(edges[i].v0, edges[i].v1);
	 send_int_array(&j, 1);
	 send_int_array(&edges[i].v0, 1);
	 send_int_array(&edges[i].v1, 1);
	 send_int_array(&key, 1);
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
   }
}

/*===========================================================================*/

void draw_edge_set_from_userind(int dg_id, char *name,
				int edgenum, int *userind)
{
   if (dg_id){
      int i, v0, v1, key, s_bufid;

      key = 0;
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      for (i = 0; i < edgenum; i++){
	 BOTH_ENDS(userind[i], &v0, &v1);
	 send_int_array(userind + i, 1);
	 send_int_array(&v0, 1);
	 send_int_array(&v1, 1);
	 send_int_array(&key, 1);
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
   }
}

/*===========================================================================*/

void draw_weighted_edge_set(int dg_id, char *name,
			    int edgenum, int *userind,
			    double *value, double etol)
{
   if (dg_id){
      int i, v0, v1, key, s_bufid;
      char dashpattern[MAX_DASH_PATTERN_LENGTH +1];
      char weight[MAX_WEIGHT_LENGTH +1];

      strcpy(dashpattern, "4 3");
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      for (i = 0; i < edgenum; i++){
	 if (!value[i]) continue;
	 BOTH_ENDS(userind[i], &v0, &v1);
	 send_int_array(userind + i, 1);
	 send_int_array(&v0, 1);
	 send_int_array(&v1, 1);
	 if (value[i] > 1-etol && value[i] < 1 + etol){
	    strcpy(weight, "1");
	    key = 8;
	 }else{
	    sprintf(weight, "%.3f", value[i]);
	    key = 10;
	 }
	 send_int_array(&key, 1);
	 send_str(weight);
	 if (key & 2)
	    send_str(dashpattern);
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
   }
}

/*===========================================================================*/

void display_support_graph(int dg_id, int clone, char *name,
			   int edgenum, int *userind,
			   double *value, double etol, int total_edgenum,
			   int report)
{
   double *weights = (double *) calloc(edgenum, DSIZE);
   int *inds = (int *) calloc(edgenum, ISIZE);
   int i, j, tmp = 0;

   for (i = 0; i < edgenum; i++){
      if (userind[i] < total_edgenum){
	 weights[i] += value[i];
	 inds[i] = userind[i];
      }else{
	 for (j = 0; j < edgenum; j++){
	    if (userind[i] == userind[j] + total_edgenum){
	       weights[j] += value[i];
	       weights[i] = 0;
	       tmp++;
	       break;
	    }
	 }
	 if (j == edgenum){
	    weights[i] += value[i];
	    inds[i] = userind[i] - total_edgenum;
	 }
      }
   }

   qsort_di(weights, inds, edgenum);
	   
   if (dg_id){
      copy_node_set(dg_id, clone, name);
      draw_weighted_edge_set(dg_id, name, edgenum-tmp, inds+tmp, weights+tmp,
			     etol);
      display_graph(dg_id, name);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
   free(weights);
   free(inds);
}

/*===========================================================================*/

void display_support_graph_flow(int dg_id, int clone, char *name,
				int edgenum, int flow_start, int *userind,
				double *value, double etol, int total_edgenum,
				int report)
{
   int i, j, tmp = 0;
   double *flow_vals = (double *) calloc(flow_start, DSIZE);
   int *inds = (int *) calloc(flow_start, ISIZE);
   
   for (i = 0; i < flow_start; i++){
      if (userind[i] < total_edgenum){
	 for (j = flow_start; j < edgenum; j++){
	    if (userind[j] == userind[i] + 2*total_edgenum){
	       flow_vals[i] += value[j];
	       break;
	    }
	 }
      }else if (userind[i] < 2*total_edgenum){
	 for (j = flow_start; j < edgenum; j++){
	    if (userind[j] == userind[i] + 2*total_edgenum){
	       flow_vals[i] += value[j];
	    }
	 }
      }
   }

   for (i = 0; i < flow_start; i++){
      if (userind[i] < total_edgenum){
	 inds[i] = userind[i];
      }else{
	 for (j = 0; j < edgenum; j++){
	    if (userind[i] == userind[j] + total_edgenum){
	       flow_vals[j] -= flow_vals[i];
	       flow_vals[j] = fabs(flow_vals[j]);
	       flow_vals[i] = 0;
	       break;
	    }
	 }
	 if (j == edgenum){
	    inds[i] = userind[i] - total_edgenum;
	 }
      }
   }

   qsort_di(flow_vals, inds, flow_start);
	   
   for (tmp = 0; flow_vals[tmp] < etol; tmp++);
   
   if (dg_id){
      copy_node_set(dg_id, clone, name);
      draw_weighted_edge_set(dg_id, name, flow_start-tmp, inds+tmp,
			     flow_vals+tmp, etol);
      display_graph(dg_id, name);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
   
   free(flow_vals);
}

/*===========================================================================*/

void display_compressed_support_graph(int dg_id, int clone, char *name,
				      int edgenum, int *userind,
				      double *value, int report)
{
   if (dg_id){
      int s_bufid, i;

      copy_node_set(dg_id, clone, name);
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = CNRP_CTOI_DRAW_FRAC_GRAPH;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      send_int_array(userind, edgenum);
      send_dbl_array(value, edgenum);
      send_msg(dg_id, CTOI_USER_MESSAGE);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
}

/*===========================================================================*/

void display_part_tour(int dg_id, int clone, char *name, int *tour,
		       int numroutes, int report)
{
   if (dg_id){
      int v0 = 0, v1 = tour[0], nv1, nv0;
      int s_bufid, i, j;
      int edgenum = 0, key = 0;

      copy_node_set(dg_id, TRUE, name);

      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      /*first count the number of edges*/
      edgenum++;
      while (v1 != numroutes){
	 v1 = tour[v0=v1];
	 edgenum++;
      }
      send_int_array(&edgenum, 1);
      /*Now reset and pack the edges themselves*/
      v0 = 0;
      v1 = tour[0];
      nv1 = v1>numroutes?v1-numroutes:0;
      nv0 = v0>numroutes?v0-numroutes:0;
      j = INDEX(nv0,nv1);
      send_int_array(&j, 1);
      send_int_array(&nv0, 1);
      send_int_array(&nv1, 1);
      send_int_array(&key, 1);
      while (v1 != numroutes){
	 v1 = tour[v0=v1];
	 nv1 = v1>numroutes?v1-numroutes:0;
	 nv0 = v0>numroutes?v0-numroutes:0;
	 j = INDEX(nv0,nv1);
	 send_int_array(&j, 1);
	 send_int_array(&nv0, 1);
	 send_int_array(&nv1, 1);
	 send_int_array(&key, 1);
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
      display_graph(dg_id, name);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
}

/*===========================================================================*/

void disp_lb(int dg_id, int clone, char *name, int *tree,
	     dbl_edge_data *best_edges, int vertnum,
	     int numroutes, int report)
{
   if (dg_id){
      int i, j, s_bufid, zero = 0;
      int edgenum = vertnum + numroutes - 1;
  
      copy_node_set(dg_id, clone, name);
      
      s_bufid = init_send(DataInPlace);
      send_str(name);
      i = MODIFY_ADD_EDGES;
      send_int_array(&i, 1);
      send_int_array(&edgenum, 1);
      for (i=1; i < vertnum; i++){
	 j = INDEX(i, tree[i]);
	 send_int_array(&j, 1);
	 send_int_array(&i, 1);
	 send_int_array(tree+i, 1);
	 send_int_array(&zero, 1);
      }
      
      for (i=0; i < numroutes; i++){
	 j = INDEX(best_edges[i].v0, best_edges[i].v1);
	 send_int_array(&j, 1);
	 send_int_array(&best_edges[i].v0, 1);
	 send_int_array(&best_edges[i].v1, 1);
	 send_int_array(&zero, 1);
      }
      i = MODIFY_END_OF_MESSAGE;
      send_int_array(&i, 1);
      send_msg(dg_id, CTOI_MODIFY_GRAPH);
      display_graph(dg_id, name);
      if (report == CTOI_WAIT_FOR_CLICK_NO_REPORT ||
	  report == CTOI_WAIT_FOR_CLICK_AND_REPORT)
	 wait_for_click(dg_id, name, report);
   }
}


