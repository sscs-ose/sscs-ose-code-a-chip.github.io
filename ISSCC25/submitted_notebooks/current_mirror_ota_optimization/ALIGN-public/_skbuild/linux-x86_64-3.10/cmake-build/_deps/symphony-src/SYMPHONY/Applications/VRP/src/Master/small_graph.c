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
#include <stdio.h>
#include <stdlib.h>    /* malloc() is here in AIX ... */
#include <string.h>

/* VRP include files */
#include "vrp_types.h"
#include "small_graph.h"
#include "vrp_master_functions.h"
#include "compute_cost.h"

/*===========================================================================*/

/*===========================================================================*\
 * Pick the cheapest edges incident to the nodes, and list them in
 * g->edges st. the lower numbered nodes are the first in every node pair.
\*===========================================================================*/

void make_small_graph(vrp_problem *p, int plus_edges)
{
   closenode *closenodes;
   int cost;
   int ch, pos, last;
   int v, w;
   edge_data *nextedge;
   small_graph *g;
   distances *dist = &p->dist;
   int k_closest = p->par.k_closest;
  
   /*------------------------------------------------------------------------*\
    * While the others processes are working, pick the cheapest edges incident
    * to each of the nodes
   \*------------------------------------------------------------------------*/
   closenodes = (closenode *)
      calloc (p->vertnum, sizeof(closenode));
  
   g = p->g = (small_graph *) calloc (1, sizeof(small_graph));
   g->vertnum = p->vertnum;
   g->allocated_edgenum = (k_closest+1) * (p->vertnum-1) + plus_edges;
   g->edges = (edge_data *) calloc
      (g->allocated_edgenum, sizeof(edge_data)); 
   
   for (v=0, nextedge=g->edges; v < p->vertnum; v++){
      /*---------------------------------------------------------------------*\
      |            Using binary tree pick the k closest node to v.            |
      \*---------------------------------------------------------------------*/
      for (last=0, w=0; w < p->vertnum; w++){
	 if (v == w) 
	    continue;
	 cost = ICOST(dist, v, w);
	 if ((last < k_closest) || ((last < p->vertnum) && (!v))){
	    pos = ++last;
	    while ((ch=pos/2) != 0){
	       if (closenodes[ch].cost >= cost) break;
	       (void) memcpy ((char *)(closenodes+pos),
			      (char *)(closenodes+ch), sizeof(closenode));
	       pos = ch;
	    }
	 }else{
	    if (closenodes[1].cost <= cost) 
	       continue;
	    pos = 1;
	    while ((ch=2*pos) < last){
	       if (closenodes[ch].cost < closenodes[ch+1].cost)
		  ch++;
	       if (cost >= closenodes[ch].cost)
		  break;
	       (void) memcpy ((char *)(closenodes+pos),
			      (char *)(closenodes+ch), sizeof(closenode));
	       pos = ch;
	    }
	    if (ch == last)
	       if (cost < closenodes[ch].cost){
		  (void) memcpy ((char *)(closenodes+pos),
				 (char *)(closenodes+ch), sizeof(closenode));
		  pos = ch;
	       }
	 }
	 closenodes[pos].node = w;
	 closenodes[pos].cost = cost;
      }
    
      /*---------------------------------------------------------------------*\
      |            Record those close edges in g->edges.                      |
      \*---------------------------------------------------------------------*/
      for (pos=last; pos>0; pos--){
	 if ((w=closenodes[pos].node) < v){
	    nextedge->v0 = w;
	    nextedge->v1 = v;
	 }else{
	    nextedge->v0 = v;
	    nextedge->v1 = w;
	 }
	 (nextedge++)->cost = closenodes[pos].cost;
      }
   }
   
   g->edgenum = (k_closest+1) * (p->vertnum-1);
   free ((char *)closenodes);
   delete_dup_edges(g);
}

/*===========================================================================*/

void save_small_graph(vrp_problem *vrp)
{
   FILE *sgfile;
   small_graph *g = vrp->g;
   edge_data *ed;
   int i, j;
   _node *tour;

   if ((sgfile = fopen(vrp->par.small_graph_file, "w")) == NULL){
      printf(" **************** Couldn't open small_graph_file for save!!\n");
      return;
   }
   fprintf(sgfile, "p %5i %7i\n", g->vertnum, g->edgenum);
   for (i=g->edgenum, ed=g->edges; i; i--, ed++)
      fprintf(sgfile, "a %5i %5i %i\n", ed->v0, ed->v1, ed->cost);

   tour = vrp->cur_tour->tour;
   fprintf(sgfile, "cost %i\n", vrp->cur_tour->cost);
   fprintf(sgfile, "numroutes %i\n", vrp->cur_tour->numroutes);
   for (j = 0; j < g->vertnum; j++)
      fprintf(sgfile, "%i %i\n", tour[j].next, tour[j].route);

   fclose(sgfile);
}

/*===========================================================================*/

void read_small_graph(vrp_problem *vrp)
{
   FILE *sgfile;
   small_graph *g;
   edge_data *ed;
   int i, j;
   _node *tour;

   if ((sgfile = fopen(vrp->par.small_graph_file, "r")) == NULL){
      printf(" **************** Couldn't open small_graph_file for load!!\n");
      exit(-1);
   }
   g = vrp->g = (small_graph *) calloc (1, sizeof(small_graph));
   fscanf(sgfile, "p %5i %7i\n", &g->vertnum, &g->edgenum);
   g->allocated_edgenum = g->edgenum;
   g->del_edgenum = 0;
   g->edges = (edge_data *) malloc (g->edgenum * sizeof(edge_data));

   for (i=g->edgenum, ed=g->edges; i; i--, ed++)
      fscanf(sgfile, "a %5i %5i %i\n", &ed->v0, &ed->v1, &ed->cost);

   tour = vrp->cur_tour->tour;
   fscanf(sgfile, "cost %i\n", &vrp->cur_tour->cost);
   fscanf(sgfile, "numroutes %i\n", &vrp->cur_tour->numroutes);
   for (j=0; j<g->vertnum; j++)
      fscanf(sgfile, "%i %i\n", &tour[j].next, &tour[j].route);
   
   fclose(sgfile);
}
