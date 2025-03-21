/* Create a data set named 'mydata' */
data mydata;
  input id $ age salary;
  datalines;
  1  25 50000
  2  30 60000
  3  28 55000
  ;
run;

/* Add a new variable called 'bonus' and assign a value based on salary*/
data mydata;
  set mydata;
  if salary > 55000 then bonus = 5000;
  else bonus = 2500;
run;

/* Print the data set*/
proc print data=mydata;
  run;
