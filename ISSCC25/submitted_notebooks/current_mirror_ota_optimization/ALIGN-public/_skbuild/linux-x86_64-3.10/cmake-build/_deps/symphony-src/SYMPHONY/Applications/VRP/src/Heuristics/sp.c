/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include "sp.h"

/*----------------------------------------------------------------*\
| This next routine computes the shortest path in a graph using    |
| a naive implementation of Dyjkstra's shortest path algorithm. d  |
| contains the current best distance to the node in questions and  |
| pi represents the shortest path tree so that pi[node] is the     |
| predecessor of node on a shortest path from the origin. An       |
| adjacency list is the data structure used by the algorithm to    |
| access the graph.
\*----------------------------------------------------------------*/

int *sp(adj_list **adj, int numnodes, int origin,
	    int dest)
{
  int *d, mincost;
  register int i, j;
  int *pi, minindex=0;
  adj_list *temp;

  d = (int *) malloc (numnodes*sizeof(int));
  pi = (int *) calloc (numnodes, sizeof(int));

  /* First set all the distances to infinity */

  for (i= 1; i<numnodes; i++)
    d[i] = MAXINT;

  /* Now set the distances of the nodes adjacent to the origin */

  temp = adj[origin];
  while (temp != NULL){
    d[temp->custnum] = temp->cost;
    temp = temp->next;
  }

  /*--------------------------------------------------------------*\
  | In each iteration, we search for the nopde with the smallest   |
  | d-value, set that value to -1 indicating that node is in the   |
  | shortest path tree, and add the node to the shortest path tree |
  | We stop when we scan the destination node. Note that the last  |
  | node on the path to the origin does not actually point to the  |
  | origin. It points to zero so that we can use this routine to   |
  | find shortest cycles. This is actually what we want to do.     |
  \*--------------------------------------------------------------*/

  for (i=1; i<numnodes; i++){
    mincost = MAXINT;
    for (j=1; j<numnodes; j++)
      if ((d[j]>=0)&&(d[j]<mincost)){
	mincost = d[j];
	minindex = j;
      }
    temp = adj[minindex];
    while (temp != NULL){
      if (d[temp->custnum] > d[minindex] + temp->cost){
	d[temp->custnum] = d[minindex] +temp->cost;
	pi[temp->custnum] = minindex;
      }
      temp = temp->next;
    }
    if (minindex == dest) break;
    d[minindex] = -1;
  }
  return(pi);
}

/*===========================================================================*/

/*---------------------------------------------------------------------*\
| This routine partitions the TSP tour into feasible routes for a VRP   |
| solution by using a shortest path algorithm to find the optimal points|
| to break the TSP tour.                                                |
\*---------------------------------------------------------------------*/

void make_routes(heur_prob *p, _node *tsp_tour, int start,
			best_tours *new_tour)
{
  int cur_node, prev_node,  route_beg, prev_route_beg;
  int weight, i, capacity = p->capacity;
  int cur_route = 1;
  int cost;
  _node *tour = new_tour->tour;
  adj_list **adj;
  adj_list *temp, *path;
  int *pi, route_end;
  int vertnum = p->vertnum;
  int *demand = p->demand;

  adj = (adj_list **) calloc (vertnum, sizeof(adj_list *));

  /*--------------------------------------------------------------------*\
  | First we must construct the graph to give to the shortest path       |
  | algorithm. In this graph, the edge costs are as follows. The cost of |
  | edge between nodes i and j is the cost of a route beginning with i's |
  | successor on the TSP tour and ending with j (in bewtween, the route  |
  | follows the same ordering as the TSP tour itself) if this is a       |
  | feasible route and infinity otherwise. Now if we find a              |
  | shortest cycle in this graph, then the nodes in the cycle will be the|
  | endpoints of the routes in an optimal partition. This is what I do.  |
  | We need to arbitrarily specify the fist endpoint in advance.         |
  | This is the value contained the start variable. The tsp_tour         |
  | structure contains the original TSP tour.                            |
  \*--------------------------------------------------------------------*/ 

  for (prev_route_beg = start, route_beg = tsp_tour[start].next, i=0;
       i<vertnum-1; prev_route_beg = route_beg,
       route_beg = tsp_tour[route_beg].next, i++){
    cur_node = route_beg;
    prev_node = 0;
    temp = adj[prev_route_beg] = (adj_list *) calloc (1, sizeof(adj_list));
    weight = demand[cur_node];
    cost = ICOST(&p->dist, prev_node, cur_node);
    temp->cost = cost + ICOST(&p->dist, 0, cur_node);
    temp->custnum = cur_node;
    prev_node = cur_node;
    cur_node = tsp_tour[cur_node].next;
    while (weight + demand[cur_node] <= capacity){
      weight += demand[cur_node];
      cost += ICOST(&p->dist, prev_node, cur_node);
      temp->next = (adj_list *) calloc (1, sizeof(adj_list));
      temp = temp->next;
      temp->cost = cost + ICOST(&p->dist, 0, cur_node);
      temp->custnum = cur_node;
      prev_node = cur_node;
      cur_node = tsp_tour[cur_node].next;
    }
  }
 
  /* The graph is constructed. Now find a shortest cycle in it */

  pi = sp(adj, vertnum, start, start);

  /*--------------------------------------------------------------------*\
  | Now the shortest cycle information is contained in pi. However, using|
  | pi, we can only trace the shortest cycle in one direction since it is|
  | actually stored as a directed path from the start node to itself.    |
  | Also, we can only trace the TSp tour in one direction since it is    |
  | stored in the same way. So we must store the cycle in the reverse    |
  | direction in order to break up the TSP tour. That is what this piece |
  | of code does. It stores the nodes on the cycle in opposite order in a|
  | linked list to be used in the next part of the code.                 |
  \*--------------------------------------------------------------------*/

  path = (adj_list *) calloc (1, sizeof(adj_list));
  path->custnum = start;
  cur_node = pi[start];
  while (cur_node){
    temp = (adj_list *) calloc (1, sizeof(adj_list));
    temp->custnum = cur_node;
    temp->next = path;
    path = temp;
    cur_node = pi[cur_node];
  }
  temp = path;

  /*--------------------------------------------------------------------*\
  | Now we have the optimal break points stored in order in a liked list.|
  | We trace the TSP tour, copying each node into the VRP tour until we  |
  | reach the endpoint of a route and then we change the route number.   |
  \*--------------------------------------------------------------------*/

  tour[0].next = tsp_tour[start].next;
  cur_node = tour[0].next;
  route_end = temp->custnum;
  for (i=1; i<vertnum-1; i++){
    tour[cur_node].next = tsp_tour[cur_node].next;
    tour[cur_node].route = cur_route;
    if (cur_node == route_end){
      cur_route++;
      if (temp->next){
	temp = temp->next;
	route_end = temp->custnum;
      }
      else break;
    }
    cur_node = tsp_tour[cur_node].next;
  }
  tour[cur_node].next = 0;
  tour[cur_node].route = cur_route;

  new_tour->cost = compute_tour_cost(&p->dist, tour);
  new_tour->numroutes = cur_route;
}    
    
      
	
	
	
	
      
      
