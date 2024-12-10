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

#ifndef _BINOMIAL_H
#define _BINOMIAL_H

#include <memory.h>

#include "sym_proto.h"

/*----------------------------------------------------------------------*\
| The structure tree_node is the structure used in the binomial heaps    |
| that I employ in savings2 in order to keep track of the savings        |
| numbers associated with each node.  The degree field denotes the       |
| degree of that node in the tree, the parent field points to the parent |
| node, the child field points to the left-most child of the node, and   |
| the sibling field points to the right sibling. The other field contain |
| the information about the node's savings number -- savings contains    |
| its value while node1 and node2 denote the nodes between which it can  |
| be inserted in order to obtain that savings number.                    |
\*----------------------------------------------------------------------*/

typedef struct TREE_NODE{
  struct TREE_NODE *parent;
  int degree;
  int cust_num;
  int savings;
  int node1;
  int node2;
  struct TREE_NODE *child;
  struct TREE_NODE *sibling;
}tree_node;

tree_node *find_max PROTO((tree_node *head));
tree_node *make_heap PROTO((int custnum, int savings,
	   int node1, int node2));
tree_node *merge_heaps PROTO((tree_node *head1, tree_node *head2));
tree_node *heap_insert PROTO((
	   tree_node * head, int cust_num, int savings,
	   int node1, int node2));
tree_node *extract_max PROTO((tree_node *head, tree_node *max_ptr));
int print_tree  PROTO((tree_node *head));
void link_trees PROTO((tree_node *tree1, tree_node *tree2));
tree_node *merge_roots PROTO((tree_node *head1, tree_node *head2));
tree_node *reverse_list PROTO((tree_node *head));
void exchange_data PROTO((tree_node *tree_node1, tree_node *tree_node2));
void update PROTO((tree_node *cur_node, int savings, int node1,
	    int node2));

#endif

