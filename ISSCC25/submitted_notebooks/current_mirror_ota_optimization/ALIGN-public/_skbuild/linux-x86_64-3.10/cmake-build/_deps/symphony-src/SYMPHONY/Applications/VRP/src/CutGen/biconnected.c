/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
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

/* SYMPHONY include files */
#include "sym_constants.h"

/* VRP include files */
#include "vrp_cg.h"

/*===========================================================================*\
 * This file contains functions for finding biconnected components.
\*===========================================================================*/

/*===========================================================================*/

void depth_first_search(vertex *v, int *count1, int *count2)
{
   register elist *e;
   char has_child = FALSE, has_non_tree_edge = FALSE;
   char is_art_point = TRUE;
   int c, min;
   
   v->scanned = TRUE;
   min = v->dfnumber = ++(*count1);
   for (e = v->first; e; e = e->next_edge){
      if (!e->other_end) continue;
      if (!e->other->scanned){
	 e->data->tree_edge = TRUE;
	 depth_first_search(e->other, count1, count2);
	 has_child = TRUE;
      }
      c = e->other->dfnumber;
      if (e->data->tree_edge && (c > v->dfnumber)){
	 if (min > e->other->low)
	    min = e->other->low;
	 if (e->other->low < v->dfnumber)
	    is_art_point = FALSE;
      }else if (!e->data->tree_edge){
	 has_non_tree_edge = TRUE;
	 if (c < v->dfnumber){
	    if (min > c){
	       min = c;
	    }
	 }
      }
   }
   v->low = min;
   if (!has_child && has_non_tree_edge) is_art_point = FALSE;
   v->is_art_point = is_art_point;

   return;
}

/*===========================================================================*/

int biconnected(network *n, int *compnodes, int *compdemands,
		double *compcuts)
{
   int i, vertnum = n->vertnum;
   vertex *verts = n->verts;
   elist *e;
   int count1 = 0, count2 = 0;
   int num_comps = 0;
   char is_art_point;
   
   verts[0].scanned = TRUE;
   verts[0].comp = 0;
   for (i=1; i<vertnum; i++)
      verts[i].scanned = FALSE;

   for(i = 1; i < vertnum; i++){
      if (!verts[i].scanned){
	 is_art_point = FALSE;
	 verts[i].low = verts[i].dfnumber = ++count1;
	 verts[i].scanned = TRUE;
	 e = verts[i].first;
	 if (!e->other_end){
	    if (e->next_edge)
	       e = e->next_edge;
	    else
	       continue;
	 }
	 e->data->tree_edge = TRUE;
	 depth_first_search(e->other, &count1, &count2);
	 is_art_point = e->other->is_art_point;
	 for(e = e->next_edge; e; e = e->next_edge){
	    if (!e->other_end) continue;
	    if (!e->other->scanned){
	       is_art_point = TRUE;
	       e->data->tree_edge = TRUE;
	       depth_first_search(e->other, &count1, &count2);
	    }
	 }
	 verts[i].is_art_point = is_art_point;
      }
   }

   for (i=1; i<vertnum; i++)
      verts[i].scanned = FALSE;

   for (i = 1; i < vertnum; i++){
      if (!verts[i].scanned){
	 verts[i].scanned = TRUE;
	 verts[i].comp = ++num_comps;
	 for (e = verts[i].first;e; e = e->next_edge){
	    if (!e->other_end) continue;
	    if (!e->other->scanned)
	       compute_comp_nums(e->other, verts[i].comp, &num_comps,
				 verts[i].is_art_point);
	 }
      }
   }
      

   for (i = 1; i < vertnum; i++){
      compnodes[verts[i].comp]++;
      compdemands[verts[i].comp] += verts[i].demand;
      for (e = verts[i].first; e; e = e->next_edge){
	 if (e->other->comp != verts[i].comp)
	    compcuts[verts[i].comp] += e->data->weight;
      }
   }

   return (num_comps);
}

/*===================================================================*/

void compute_comp_nums(vertex *v, int parent_comp, int *num_comps,
		       char parent_is_art_point)
{
   elist *e;

   v->scanned = TRUE;
   if (parent_is_art_point && v->is_art_point)
      v->comp = ++(*num_comps);
   else
      v->comp = parent_comp;
   for (e = v->first;e ; e = e->next_edge){
      if (!e->other_end) continue;
      if (!e->other->scanned)
	 compute_comp_nums(e->other, v->comp, num_comps,
			   v->is_art_point);
   }
}
   
       
      
