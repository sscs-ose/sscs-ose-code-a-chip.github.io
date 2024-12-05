BEGIN{
   print_on = 1;
}

($1=="/*__BEGIN_EXPERIMENTAL_SECTION__*/"){
   print_on = 0;
}

($1=="#__BEGIN_EXPERIMENTAL_SECTION__#"){
   print_on = 0;
}

($1=="/*___END_EXPERIMENTAL_SECTION___*/"){
   print_on = 1;
}

($1=="#___END_EXPERIMENTAL_SECTION___#"){
   print_on = 1;
}

($1=="/*UNCOMMENT"){
   getline;
   getline;
   while ($1 != "#endif"){
      print;
      getline;
   }
   getline;
}

#($1=="/*" && $8=="Common"){
#  getline;
#  printf("/* This software is licensed under the Common Public License Version 1.0.    */\n");
#}

#($1=="/*" && $2=="accompanying"){
#  getline;
#  printf("/* Please see accompanying file for terms.                                   */\n");
#}

($1!="/*___END_EXPERIMENTAL_SECTION___*/" && $1!="/*__BEGIN_EXPERIMENTAL_SECTION__*/" && $1!="/*UNCOMMENT*/" && $1!="#___END_EXPERIMENTAL_SECTION___#" &&
$1!="#___END_EXPERIMENTAL_SECTION___#"){
   if (print_on){
      print;
   }
}

END{
}







