# Orchestrator (aka Offer-Enhancer-and-Ranker core)

The Orchestrator, or Offer-Enhancer-and-Ranker core, manages the workflows of the whole system, from the extraction of the TRIAS data containing the trip request, up to the ranking of the offers. It sets up the connection between the different components, makes sure that the dependencies between them are respected, handles the errors, writes into the log. 

The system pipeline can be summarized as follows: 

- The Orchestrator sends a request to the trias-extractor (described in Section 5.4.1 of D3.1), which extracts the trip request data and stores it into the cache; 
- The Orchestrator sends a request to the Feature Enhancer, which assigns a city name to offers and updates the cache; 
- The Orchestrator sends asynchronous requests to OC core, Data Provider and Incentive Provider, each of which writes the newly obtained data into the cache; 
- The Orchestrator sends a request to THOR, which returns the offer ranking. 

 ### Usage 

The service is deployed as a Docker container and can be launched with the `docker-compose up` command, which brings it up together with the all the rest of components, including the trias-extractor, the offer cache, the offer categorizer (OC core and feature collectors), the data-provider and the incentive-provider.

Example of request:

```
curl --header 'Content-Type: application/xml' \
--request POST \
--data-binary '@trias-extractor/trias/subset_4_no_10_tsp_025.xml' 
http://localhost:5000/compute
```

The response is a JSON with the following structure: 
```
{ 
  "result": [ 
    { 
      "blockchain-incentives": { 
        "10discount": false,  
        "20discount": false,  
        "trainSeatUpgrade": false 
      },  
      "categories": { 
        "cheap": 0.6852,  
        "comfortable": 0.209,  
        "door-to-door": 0.0,  
        "environmentally_friendly": 0.0,  
        "healthy": 0.0,  
        "multitasking": 0,  
        "panoramic": 0.0,  
        "quick": 0.9043999999999999,  
        "reliable": 0.5376,  
        "short": 0.0764 
      },  
      "offer_id": "dd19551d-7e9e-45b1-9442-3482e5d92055",  
      "ranking": { 
        "rank": 1,  
        "score": 0.856291038154392 
      } 
    },  
    { 
      "blockchain-incentives": { 
        "10discount": false,  
        "20discount": false,  
        "trainSeatUpgrade": false 
      },  
      "categories": { 
        "cheap": 0.162,  
        "comfortable": 0.1493,  
        "door-to-door": 0.0,  
        "environmentally_friendly": 1.0,  
        "healthy": 0.0,  
        "multitasking": 0.0,  
        "panoramic": 0.0,  
        "quick": 0.3942,  
        "reliable": 0.1884,  
        "short": 0.9236 
      },  
      "offer_id": "fd796c85-0afe-44ae-86f1-2c2f0c70f444",  
      "ranking": { 
        "rank": 0,  
        "score": 1.0 
      } 
    } 
  ] 
}
```
