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

#include "sym_constants.h"
#include "tsp_ins_rout.h"
#include "vrp_const.h"
#include "compute_cost.h"
#include <string.h>
/*-------------------------------------------------------------------------*\
| These subroutines are used to construct TSp tours usinf simple insertion  |
| heuristics. The tours are then used in route first - cluster second       |
| algorithms                                                                |
\*-------------------------------------------------------------------------*/
	
/*===========================================================================*/

int tsp_farthest_ins_from_to(heur_prob *p, _node *tour, int cost, int from_size, 
			 int to_size, int starter, neighbor *nbtree, 
			 int *intour, int *last)
{
  int farnode, size;
  
  for (size = from_size; size < to_size; size++){
    farnode = tsp_farthest(nbtree, intour, last);
    intour[farnode] = IN_TOUR;
    cost += tsp_insert_into_tour(p, tour, starter, size, farnode);
    tsp_fi_insert_edges(p, farnode, nbtree, intour, last);
  }
  return(cost);
}

/*===========================================================================*/

int tsp_nearest_ins_from_to(heur_prob *p, _node *tour, int cost, int from_size, 
			int to_size, int starter, neighbor *nbtree, 
			int *intour, int *last)
{
  int nearnode, size;
  
  for (size = from_size; size < to_size; size++){
    nearnode = tsp_closest(nbtree, intour, last);
    intour[nearnode] = IN_TOUR;
    cost += tsp_insert_into_tour(p, tour, starter, size, nearnode);
    tsp_ni_insert_edges(p, nearnode, nbtree, intour, last);
  }
  return(cost);
}

/*===========================================================================*/

int tsp_closest(neighbor *nbtree, int *intour, int *last)
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

void tsp_ni_insert_edges(heur_prob *p, int new_node, neighbor *nbtree, int *intour, 
		     int *last)
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
    if ( intour[i] != IN_TOUR){
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

int tsp_farthest(neighbor *nbtree, int *intour, int *last)
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

void tsp_fi_insert_edges(heur_prob *p, int new_node, neighbor *nbtree, int *intour,
		     int *last)
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
    if ( intour[i] != IN_TOUR){
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

int tsp_insert_into_tour(heur_prob *p, _node *tour, int starter, int size, 
		     int new_node)
{
  int change = 0, minchange = MAXINT;
  int i, iminchange = 0;
  int v0, v1;

  /*-------------------------------------------------------------------------*\
  | Here we search for the cheapest place to insert the new customer on the   |
  | tour and insert it in that position. Then tour data structures must be    |
  | updated accordingly                                                       |
  \*-------------------------------------------------------------------------*/
  
  for (i=0, minchange = MAXINT, v1=starter; i<size; i++){
    v0 = v1;
    v1 = tour[v0].next;
    change = (ICOST(&p->dist, v0,new_node) + ICOST(&p->dist, new_node,v1)) - ICOST(&p->dist, v0,v1);
    if (change < minchange){
      minchange = change;
      iminchange = v0;
    }
  }
  v1 = tour[v0 = iminchange].next;
  tour[new_node].next = v1;
  tour[v0].next = new_node;
  return(minchange);
}
