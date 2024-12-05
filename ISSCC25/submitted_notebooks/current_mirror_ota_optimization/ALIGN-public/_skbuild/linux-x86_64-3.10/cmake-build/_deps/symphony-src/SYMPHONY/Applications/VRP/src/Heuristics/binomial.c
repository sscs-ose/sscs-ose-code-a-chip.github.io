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

#include <stdio.h>

#include "sym_constants.h"
#include "sym_macros.h"
#include "binomial.h"
#include "vrp_const.h"
#include <stdlib.h>


/*-----------------------------------------------------------------------*\
| The functions in this file are the standard operations on binomial heaps|
| I will not bother to comment each one of them. See a standard data      |
| structures text for an explanation of these algorithms                  |
\*-----------------------------------------------------------------------*/

tree_node *make_heap(int cust_num, int savings, int node1,
		     int node2)
{
  tree_node *head;

  head = (tree_node *) calloc (1, sizeof(tree_node));

  head->cust_num = cust_num;
  head->savings = savings;
  head->node1 = node1;
  head->node2 = node2;

  return(head);
}

/*===========================================================================*/

tree_node *find_max(tree_node *head)
{
  tree_node *max_ptr = NULL, *temp;
  register int max_val = (-1)*MAXINT;

  temp = head;
  while (temp != NULL){
    if (temp->savings > max_val){
      max_val = temp->savings;
      max_ptr = temp;
    }
    temp = temp->sibling;
  }
  return(max_ptr);
}

/*===========================================================================*/

void link_trees(tree_node *tree1, tree_node *tree2)
{
tree1->parent = tree2;
tree1->sibling = tree2->child;
tree2->child = tree1;
(tree2->degree)++;
}

/*===========================================================================*/

tree_node *merge_roots(tree_node *head1, tree_node *head2)
{
  tree_node *head, *temp, *temp1, *temp2;
  int cur_deg;

  if (!head1) return(head2);
  if (!head2) return(head1);

  cur_deg = MIN(head1->degree, head2->degree);

  if (head1->degree == cur_deg){
    head = head1;
    temp = head;
    temp1 = head1->sibling;
    temp2 = head2;
  }
  else{
    head = head2;
    temp = head;
    temp2 = head2->sibling;
    temp1 = head1;
  }

  while ((temp1 != NULL) && (temp2 != NULL)){

    cur_deg = MIN(temp1->degree, temp2->degree);

    if (temp1->degree == cur_deg){
      temp->sibling = temp1;
      temp = temp->sibling;
      temp1 = temp1->sibling;
    }
    if (temp2->degree == cur_deg){
      temp->sibling = temp2;
      temp = temp->sibling;
      temp2 = temp2->sibling;
    }
  }
  if (temp1)
    temp->sibling = temp1;
  if (temp2)
    temp->sibling = temp2;

  return(head);
}

/*===========================================================================*/

tree_node *merge_heaps(tree_node *head1, tree_node *head2)
{
  tree_node *head, *cur, *next, *prev=NULL;

  head = merge_roots(head1, head2);
  if (head == NULL) return(head);
  cur = head;
  next = cur->sibling;

  if(!head1) return(head2);

  while (next != NULL){
    if ((cur->degree != next->degree) ||
	((next->sibling != NULL) && (cur->degree == next->sibling->degree))){
      prev = cur;
      cur = next;
    }
    else if (cur->savings >= next->savings){
      cur->sibling = next->sibling;
      link_trees(next, cur);
    }
    else if (prev == NULL){
      head = next;
      link_trees(cur, next);
      cur = next;
    }
    else{
      prev->sibling = next;
      link_trees(cur, next);
      cur = next;
    }
    next = cur->sibling;
  }
  
  return(head);
}

/*===========================================================================*/

tree_node *heap_insert(tree_node *head, int cust_num, int savings,
		       int node1, int node2)
{
  tree_node *temp;

  temp = make_heap(cust_num, savings, node1, node2);
  if (head == NULL)
     return(temp);

  head = merge_heaps(head, temp);

  return(head);
}

/*===========================================================================*/

tree_node *reverse_list(tree_node *head)
{
  tree_node *temp1, *temp2, *temp3;

  temp1 = head;

  if (!temp1) return(NULL);

  if (!temp1->sibling){
    temp1->parent = NULL;
    return(temp1);
  }

  if (!temp1->sibling->sibling){
    temp2 = temp1->sibling;
    temp2->parent = NULL;
    temp2->sibling = temp1;
    temp1->sibling = NULL;
    temp1->parent = NULL;
    return(temp2);
  }


  temp1 = head;
  temp1->parent = NULL;
  temp2 = temp1->sibling;
  temp2->parent = NULL;
  temp3 = temp2->sibling;
  head ->sibling = NULL;

  while (temp3 != NULL){
    temp3->parent = NULL;
    temp2->sibling = temp1;
    temp1 = temp2;
    temp2 = temp3;
    temp3 = temp3->sibling;
  }
  
  temp2->sibling = temp1;

  return(temp2);
}

/*===========================================================================*/

tree_node *extract_max(tree_node *head, tree_node *max_ptr)
{
  tree_node *temp;

  temp = head;

  if (max_ptr == head)
    head = head->sibling;
  else{
    while(temp != NULL){
      if (temp->sibling == max_ptr){
	temp->sibling = temp->sibling->sibling;
	break;
      }
      temp=temp->sibling;
    }
  }
  if (max_ptr->child){
    temp = reverse_list(max_ptr->child);
    head = merge_heaps(temp, head);
  }
  return(head);
}

/*===========================================================================*/

void exchange_data(tree_node *tree_node1, tree_node *tree_node2)
{
  int temp_savings;
  int temp_cust_num, temp_node1, temp_node2;

  temp_cust_num = tree_node1->cust_num;
  temp_savings = tree_node1->savings;
  temp_node1 = tree_node1->node1;
  temp_node2 = tree_node1->node2;
  tree_node1->cust_num = tree_node2->cust_num;
  tree_node1->savings = tree_node2->savings;
  tree_node1->node1 = tree_node2->node1;
  tree_node1->node2 = tree_node2->node2;
  tree_node2->cust_num = temp_cust_num;
  tree_node2->savings = temp_savings;
  tree_node2->node1 = temp_node1;
  tree_node2->node2 = temp_node2;
}

/*===========================================================================*/

void update(tree_node *cur_node, int savings, int node1,
	    int node2)
{
  tree_node *temp1, *temp2;

  if (savings < cur_node->savings){
    printf("\nError: illegal update call\n");
    exit(1);
  }

  cur_node->savings = savings;
  cur_node->node1 = node1;
  cur_node->node2 = node2;
  temp1 = cur_node;
  temp2 = temp1->parent;

  while ((temp2 != NULL) && (temp1->savings > temp2->savings)){
    exchange_data(temp1, temp2);
    temp1 = temp2;
    temp2 = temp1->parent;
  }
}

/*===========================================================================*/

/*-------------------------------------------------------------------------*\
| This function prints out the current heap and is for debugging purposes   |
\*-------------------------------------------------------------------------*/

int print_tree(tree_node *head)
{
  tree_node *temp;
  int count = 0;

  temp = head;

  while (temp != NULL){
    printf(" custnum = %i degree = %i savings = %i node1 = %i node2 = %i", 
	   temp->cust_num, temp->degree, temp->savings, temp->node1,
	   temp->node2);
    if (temp->parent)
      printf(" parent = %i", temp->parent->cust_num);
    printf("\n");
    count++;
    if (temp->child)
      count += print_tree(temp->child);
    temp = temp->sibling;
  }
  return(count);
}

