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

#ifndef _CNRP_DG_H
#define _CNRP_DG_H

/* SYMPHONY include files */
#include "sym_proto.h"
#include "sym_dg.h"

/* Possible scanned stati of dg_net_vertices */
#define NOT_SCANNED    0 
#define SCANNED_SHRUNK 1
#define SCANNED_ALIVE  2

typedef struct DG_NET_EDGE{
   struct DG_NET_VERTEX *head;
   struct DG_NET_VERTEX *tail;
   double                weight;  
   char                  deleted;
}dg_net_edge;

typedef struct DG_NET_ELIST{
   struct DG_NET_ELIST  *next_edge; /* next edge in the edgelist */
   dg_net_edge          *data;      /* the data of the edge */
   struct DG_NET_VERTEX *other;     /* pointer to the other end of the edge*/
}dg_net_elist;

typedef struct DG_NET_VERTEX{
   int                  degree;/*contains the degree of the node in the graph*/
   int                  orignodenum;/*the node number in the original graph*/

   struct DG_NET_ELIST *first;/*points to the 1st edge in the adjacency list*/
   struct DG_NET_ELIST *last; /*points to the last edge in the adjacency list*/

   int                  snode_size;  /*size of the supernode identified by this
				      *node. makes sense only at the 
				      *identifier. 0 to start with*/
   struct DG_NET_VERTEX *snode_next; /*the next node in the list of nodes
				      *belonging to the same supernode.
				      *NULL to start with*/

   char                 scanned;
}dg_net_vertex;

typedef struct DG_NET_NETWORK{
   int         origvertnum; /*number of vertices in the original graph*/
   int         vertnum;     /*number of supernodes in the graph*/
   int         edgenum;     /*number of edges in the graph (size of 'edges');
			     *as edges might contain unlinked edges, the real
			     *number of edges might be smaller!*/
   dg_net_elist   *adjlist; /*the array containing the adjacency lists for each
			     *node*/
   dg_net_edge    *edges;   /*the list of edges in the graph*/
   dg_net_vertex  *verts;   /*the list of vertices (everything, not just
			     *supernodes)*/
}dg_net_network;

typedef struct CNRP_DG{
   dg_net_network *n;
}cnrp_dg;


dg_net_network *dg_createnet PROTO((int vertnum,
				    int length, int *xind, double *xval));
void dg_freenet PROTO((dg_net_network *n));
void dg_net_shrink_chains PROTO((dg_net_network *n));
void copy_network_into_graph PROTO((dg_net_network *n, dg_graph *g));

#endif
