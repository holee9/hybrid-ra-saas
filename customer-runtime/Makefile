.PHONY: setup up down logs pull-model status clean

setup:
	./setup.sh

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f --tail=100

pull-model:
	docker-compose exec ollama ollama pull $$(grep OLLAMA_MODEL .env | cut -d= -f2)

status:
	docker-compose ps

clean:
	docker-compose down -v
	@echo "All volumes removed."
