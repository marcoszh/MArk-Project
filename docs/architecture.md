# Overview

```
  	users                                                       	prize_updater
       ∧                                                                ∧  	∧
       | (http)                                                         |	|
       ∨                                        						∨	|
	controller <------------------> model_server <-----------------> redis	|
                                     ∧                                      |       
                               		 |                               		|
                                     ∨                                      ∨          
	  AWS(action) <--------------> AWS_manager           				AWS(market)
   
```

