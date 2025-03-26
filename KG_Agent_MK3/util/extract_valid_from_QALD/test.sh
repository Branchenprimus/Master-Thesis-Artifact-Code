curl -G https://query.wikidata.org/sparql \
  --data-urlencode 'query=SELECT DISTINCT ?s1 WHERE { ?s1  <http://www.wikidata.org/prop/direct/P30>  <http://www.wikidata.org/entity/Q15> . ?s1  <http://www.wikidata.org/prop/direct/P31>/<http://www.wikidata.org/prop/direct/P279>*  <http://www.wikidata.org/entity/Q8072> . ?s1 <http://www.wikidata.org/prop/direct/P2044> ?o1 . } ORDER BY DESC(?o1) LIMIT 1' \
  -H 'Accept: application/sparql-results+json'
