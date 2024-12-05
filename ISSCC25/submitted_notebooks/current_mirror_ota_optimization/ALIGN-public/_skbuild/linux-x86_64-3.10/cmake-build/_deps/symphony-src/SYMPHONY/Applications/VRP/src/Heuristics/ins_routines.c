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

#include <stdlib.h>
#include <string.h>
#include "sym_constants.h"
#include "ins_routines.h"
#include "route_heur.h"
#include "vrp_const.h"
#include "compute_cost.h"

/*--------------------------------------------------------------------------*\
| These routines relate to the construction of the routings for the clusters |
| determined by the clustering algorithms                                    |
\*--------------------------------------------------------------------------*/
	
/*===========================================================================*/

int farthest_ins_from_to(heur_prob *p, _node *tour, int cost, int from_size, 
			 int to_size, int starter, neighbor *nbtree, 
			 int *intour, int *last, route_data *route_info, 
			 int cur_route)
{
  int farnode, size;
  
  for (size = from_size; size < to_size; size++){
    farnode = farthest(nbtree, intour, last);
    intour[farnode] = IN_TOUR;
    cost += insert_into_tour(p, tour, starter, size, farnode,
			     route_info, cur_route);
    fi_insert_edges(p, farnode, nbtree, intour, last, tour, cur_route);
  }
  return(cost);
}

/*===========================================================================*/

int nearest_ins_from_to(heur_prob *p, _node *tour, int cost, int from_size, 
			int to_size, int starter, neighbor *nbtree, 
			int *intour, int *last, route_data *route_info, 
			int cur_route)
{
  int nearnode, size;
  
  for (size = from_size; size < to_size; size++){
    nearnode = closest(nbtree, intour, last);
    intour[nearnode] = IN_TOUR;
    cost += insert_into_tour(p, tour, starter, size, nearnode,
			     route_info, cur_route);
    ni_insert_edges(p, nearnode, nbtree, intour, last, tour, cur_route);
  }
  return(cost);
}

/*===========================================================================*/

int closest(neighbor *nbtree, int *intour, int *last)
{
  int closest_node;
  int pos, ch;
  int cost;
  neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/
  
  closest_node = nbtree[1].nbor;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(neighbor));
  cost = nbtree[*last].cost;
  --*last;
  pos = 1;
  while ((ch=2*pos) < *last){
    if (nbtree[ch].cost > nbtree[ch+1].cost)
      ch++;
    if (cost <= nbtree[ch].cost)
      break;
    intour[nbtree[ch].nbor] = pos;
    (void) memcpy ((char *)(nbtree+pos), 
		   (char *)(nbtree+ch), sizeof(neighbor));
    pos = ch;
  }
  if (ch == *last){
    if (cost > nbtree[ch].cost){
      intour[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(neighbor));
      pos=ch;
    }
  }
  intour[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(neighbor));
  return(closest_node);
}

/*===========================================================================*/

void ni_insert_edges(heur_prob *p, int new_node, neighbor *nbtree, int *intour, 
		     int *last, _node *tour, int cur_route)

     /*-----------------------------------------------------------------------*\
     |  Scan through the edges incident to 'new_node' - the new node in the set.    |
     |  If the other end 'i' is in the set, do nothing.                        |
     |  If the other end is not in nbtree then insert it.                      |
     |  Otherwise update its distance if necessary:                            |
     |     If the previous closest point of the set to 'i' is closer then      |
     |     'new_node' then we don't have to do anything, otherwise update.          |
     |     (update: the min element is on the top of the tree                  |
     |              Therefore the insertion and the update parts can be done   |
     |              with the same code, not like in fi_insert_edges.)          |
     \*-----------------------------------------------------------------------*/

{
  int cost, prevcost;
  int pos, ch;
  int i;
  int vertnum = p->vertnum;
  
  for (i=0; i<vertnum; i++){
    if (( intour[i] != IN_TOUR) && 
	((tour[i].route == cur_route) ||
	 (tour[i].route == 0))){ /* We must check to make sure that the customer
                                    we are trying to insert is in the cluster we
                                    are routing */
      cost = ICOST(&p->dist, i, new_node);
      if (intour[i] == NOT_NEIGHBOR){
	pos = ++(*last);
	prevcost = cost+1;
      }else{
	prevcost = nbtree[pos = intour[i]].cost;
      }
      if (prevcost > cost){
	while ((ch=pos/2) != 0){
	  if (nbtree[ch].cost <= cost)
	    break;
	  intour[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = i;
	nbtree[pos].host = new_node;
	nbtree[pos].cost = cost;
	intour[i] = pos;
      }
    }
  }
}

/*===========================================================================*/

int farthest(neighbor *nbtree, int *intour, int *last)
{
  int farthest_node;
  int pos, ch;
  int cost;
  neighbor temp;

  /*-----------------------------------------------------------------------*\
  | This routine deletes the item from the top of the binary tree where the |
  | distances are stored and adjusts the tree accordingly                   |
  \*-----------------------------------------------------------------------*/

  farthest_node = nbtree[1].nbor;
  (void) memcpy ((char *)&temp, (char *)(nbtree+*last), sizeof(neighbor));
  cost = nbtree[*last].cost;
  --*last;
  pos = 1;
  while ((ch=2*pos) < *last){
    if (nbtree[ch].cost < nbtree[ch+1].cost)
      ch++;
    if (cost >= nbtree[ch].cost)
      break;
    intour[nbtree[ch].nbor] = pos;
    (void) memcpy ((char *)(nbtree+pos), 
		   (char *)(nbtree+ch), sizeof(neighbor));
    pos = ch;
  }
  if (ch == *last){
    if (cost < nbtree[ch].cost){
      intour[nbtree[ch].nbor] = pos;
      (void) memcpy ((char *)(nbtree+pos), 
		     (char *)(nbtree+ch), sizeof(neighbor));
      pos=ch;
    }
  }
  intour[temp.nbor] = pos;
  (void) memcpy ((char *)(nbtree+pos), (char *)&temp, sizeof(neighbor));
  return(farthest_node);
}

/*===========================================================================*/

void fi_insert_edges(heur_prob *p, int new_node, neighbor *nbtree, int *intour, 
		     int *last, _node *tour, int cur_route)
     /*-----------------------------------------------------------------------*\
     |  Scan through the edges incident to 'new_node' - the new node in the set.    |
     |  If the other end 'i' is in the set, do nothing.                        |
     |  If the other end is not in nbtree then insert it.                      |
     |  Otherwise update its distance if necessary:                            |
     |     If the previous closest point of the set to 'i' is closer then      |
     |     'new_node' then we don't have to do anything, otherwise update.          |
     |     (update: the max element is on the top of the tree)                 |
     \*-----------------------------------------------------------------------*/

{
  int cost;
  int pos, ch;
  int i;
  int vertnum = p->vertnum;
  
  for (i=0; i<vertnum; i++){
    if (( intour[i] != IN_TOUR) &&
	((tour[i].route == cur_route) ||
	 (tour[i].route == 0))){ /* We must check to make sure that the customer
                                    we are trying to insert is in the cluster we
                                    are routing */
      cost = ICOST(&p->dist, i, new_node);
      if (intour[i] == NOT_NEIGHBOR){ /* new neighbor, must insert it */
	pos = ++(*last);
	while ((ch=pos/2) != 0){
	  if (nbtree[ch].cost >= cost)
	    break;
	  intour[nbtree[ch].nbor] = pos;
	  (void) memcpy ((char *)(nbtree+pos), 
			 (char *)(nbtree+ch), sizeof(neighbor));
	  pos = ch;
	}
	nbtree[pos].nbor = i;
	nbtree[pos].host = new_node;
	nbtree[pos].cost = cost;
	intour[i] = pos;
      }else{  /*---- already neighbor, update it if needed ------------*/
	if (nbtree[pos = intour[i]].cost > cost){
	  while ((ch=2*pos) < *last){
	    if (nbtree[ch].cost < nbtree[ch+1].cost)
	      ch++;
	    if (cost >= nbtree[ch].cost)
	      break;
	    intour[nbtree[ch].nbor] = pos;
	    (void) memcpy ((char *)(nbtree+pos), 
			   (char *)(nbtree+ch), sizeof(neighbor));
	    pos = ch;
	  }
	  if (ch == *last){
	    if (cost < nbtree[ch].cost){
	      intour[nbtree[ch].nbor] = pos;
	      (void) memcpy ((char *)(nbtree+pos), 
			     (char *)(nbtree+ch), sizeof(neighbor));
	      pos=ch;
	    }
	  }
	  nbtree[pos].nbor = i;
	  nbtree[pos].host = new_node;
	  nbtree[pos].cost = cost;
	  intour[i] = pos;
	} /*---------- end if{ had to be updated } */
      } /*-------------- end if{ was not neighbor }else{ was neighbor} */
    } /*------------------ end if ('i' is not in the tour) */
  } /*---------------------- end for loop for all nodes */
}

/*===========================================================================*/

int insert_into_tour(heur_prob *p, _node *tour, int starter, int size, 
		     int new_node, route_data *route_info, int cur_route)
{
  int change, minchange;
  int i, iminchange = 0;
  int v0, v1;

  /*-------------------------------------------------------------------------*\
  | Here we search for the cheapest place to insert the new customer on the   |
  | tour and insert it in that position. Then tour and route_info data        |
  | structures must be updated accordingly                                    |
  \*-------------------------------------------------------------------------*/
  
  for (i=0, minchange = MAXINT, v1=starter; i<size; i++){
    v0 = v1;
    v1 = tour[v0].next;
    change = ICOST(&p->dist, v0,new_node) + ICOST(&p->dist, new_node,v1) - ICOST(&p->dist, v0,v1);
    if (change < minchange){
      minchange = change;
      iminchange = v0;
    }
  }
  v1 = tour[v0 = iminchange].next;
  tour[new_node].next = v1;
  tour[v0].next = new_node;
  if (new_node == 0){
    route_info[cur_route].last = v0;
    route_info[cur_route].first = v1;
  }
  if (v0 == 0)
    route_info[cur_route].first = new_node;
  if (v1 == 0)
    route_info[cur_route].last = new_node;
  return(minchange);
}

void starters(heur_prob *p, int *starter, route_data *route_info, 
	      int start)
{
  _node *tour;
  int numroutes, start_pos;
  int dist;
  int cur_node = 0, other_node = 0, cust;
  int cur_route, count;

  /*-------------------------------------------------------------------------*\
  | This routine computes the starters for the construction of the routings   |
  | of the clusters. For the first trial, the starter is just the node in the |
  | the cluster that is the farthest away from some other node in the cluster.|
  | Fpr all other trials, the starter is a random node on the route.          |
  \*-------------------------------------------------------------------------*/

  tour = p->cur_tour->tour;
  numroutes = p->cur_tour->numroutes;

  route_calc(&p->dist, tour, numroutes, route_info, p->demand);

  for (cur_route = 1; cur_route<=numroutes; cur_route++){
    count = 0;
    cur_node = route_info[cur_route-1].last;
    if (start == FAR_INS){
      dist = -MAXINT;
      do{
	cur_node = tour[cur_node].next;
	other_node = cur_node;
	do{
	  other_node = tour[other_node].next;
	  if (cur_route != numroutes)
	    if(other_node == route_info[cur_route+1].first)
	      other_node = 0;
	  if (ICOST(&p->dist, cur_node, other_node) > dist){
	    dist = ICOST(&p->dist, cur_node, other_node);
	    starter[cur_route-1] = cur_node;
	  }
	}while (other_node);
      }while (cur_node != route_info[cur_route].last);
    }
    else{
      start_pos = rand()%route_info[cur_route].numcust+1;
      for (cust = 1; count<start_pos; cust++)
	if (tour[cust].route == cur_route) count ++;
      starter[cur_route-1] = cust-1;
    }
  }
  return;
}
