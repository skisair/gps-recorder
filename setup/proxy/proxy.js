var http = require('http');
var httpProxy = require('http-proxy');

var normalProxy = new httpProxy.createProxyServer({
    target: {
        host: 'localhost',
        port: 8081
    },
    ws: true
});

var webSocketProxy = new httpProxy.createProxyServer({
    target: {
        host: 'localhost',
        port: 8080
    },
    ws: true
});

var server = http.createServer(function ( req, res ) {
    console.log(req.url)
    try {
        if (req.url.lastIndexOf('/socket.io/', 0) === 0) {
            normalProxy.web(req, res);
        }else if (req.url.lastIndexOf('/ws', 0) === 0) {
            webSocketProxy.web( req, res );
        } else {
            normalProxy.web( req, res );
        }
    } catch (error) {
        console.error(error);
    }

});

server.on( 'upgrade', function( req, socket, head ) {
    webSocketProxy.ws( req, socket, head );
});

server.listen(80);

console.log('It Works!');