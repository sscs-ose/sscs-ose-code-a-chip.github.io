#include <stdio.h>

int main(int argc, char **argv)
{
   FILE *f1, *f2;
   int i, j = 0;
   char key[10];
   int prev_node, node, code;
   
   f1 = fopen(argv[2], "a");
   f2 = fopen(argv[1], "r");

   node = 0;
   prev_node = 0;
   /*   while (fgets(line, 10, f2) != NULL){*/
   while ((code = fscanf(f2, "%i", &node)) >= 0){
      if (!code && node){
	 fscanf(f2, "%s", key);
	 if (strcmp("cost", key) == 0)
	    break;
	 node = 0;
	 j++;
	 if (prev_node)
	    fprintf(f1, "a %i %i %i 0\n", j, prev_node, node);
      }else if (!code){
	 fscanf(f2, "%s", key);
	 prev_node = 0;
      }else if (code == 1){
	 j++;
	 fprintf(f1, "a %i %i %i 0\n", j, prev_node, node);
	 prev_node = node;
      }
   }
   j++;
   fprintf(f1, "a %i %i %i 0\n", j, node, 0);

   fclose(f1);
   fclose(f2);
}
      
		    
   
