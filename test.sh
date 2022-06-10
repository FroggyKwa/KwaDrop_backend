docker-compose -f docker-compose.test.yml rm -f
echo "Succeeded 1"
docker-compose -f docker-compose.test.yml build
echo "Succeeded 2"
docker-compose -f docker-compose.test.yml up --exit-code-from backend --abort-on-container-exit
echo "Succeeded 3"
docker-compose -f docker-compose.test.yml rm -f
echo "Succeeded 4"
