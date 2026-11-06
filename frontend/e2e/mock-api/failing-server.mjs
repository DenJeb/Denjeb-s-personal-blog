import { createServer } from "node:http";

const server = createServer((_request, response) => {
  response.statusCode = 500;
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.end(JSON.stringify({ detail: "upstream failed" }));
});

server.listen(Number(process.env.MOCK_API_PORT ?? 8002), "127.0.0.1");
