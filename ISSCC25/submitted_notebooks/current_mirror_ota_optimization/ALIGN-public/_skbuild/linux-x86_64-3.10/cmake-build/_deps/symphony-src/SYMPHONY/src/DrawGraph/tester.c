/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The Interactive Graph Drawing application was developed by Marta Eso.     */
/*                                                                           */
/* (c) Copyright 2000-2019 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <memory.h>
#include <string.h>
#include <stdio.h>

#include "sym_proccomm.h"
#include "intermediary.h"

void main(void)
{
   char line[81];
   FILE *infile[100];
   int info, s_bufid, r_bufid, msgtag, ini, itmp, inter, debug=4;

   ini = 0;
   infile[ini] = stdin;
   spawn((char *)"intermediary", NULL, debug, NULL, 1, &inter)

   while (TRUE){
      memset(line, 0, 81);
      if (fgets(line, 80, infile[ini]) == NULL){
	 /* end of file */
	 fclose(infile[ini--]);
      }else{
	 line[strlen(line)-1] = 0;
	 if (memcmp(line, (char *)"read", 4) == NULL){
	    ini++;
	    infile[ini] = fopen(line+5, "r");
	    if (infile[ini] == NULL){
	       fprintf(stderr, "Couldn't open file '%s'\n", line+5);
	       ini--;
	    }
	 }else if (memcmp(line, (char *)"exit", 4) == NULL){
	    exit(1);
	 }else if (memcmp(line, (char *)"mtag", 4) == NULL){
	    sscanf(line+5, "%i", &msgtag);
	    s_bufid = init_send(DataInPlace);
	 }else if (memcmp(line, (char *)"emsg", 4) == NULL){
	    send_msg(inter, msgtag);
	    if (msgtag == CTOI_WAIT_FOR_CLICK_AND_REPORT){
	       r_bufid = receive_message(ANYONE, ANYTHING);
	       freebuf(r_bufid);
	    }
	 }else if (memcmp(line, (char *)"wind", 4) == NULL){
	    send_char_array(line+5, IDENT_LENGTH);
	 }else if (memcmp(line, (char *)"lbl", 3) == NULL){
	    send_char_array(line+4, LABEL_LENGTH);
	 }else if (memcmp(line, (char *)"wgt", 3) == NULL){
	    send_char_array(line+4, WEIGHT_LENGTH);
	 }else if (memcmp(line, (char *)"int", 3) == NULL){
	    sscanf(line+4, "%i", &itmp);
	    send_int_array(&itmp, 1);
	 }
      }
   }
}
