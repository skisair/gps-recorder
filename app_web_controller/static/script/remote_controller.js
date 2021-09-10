let socket = io.connect({ transports: ["polling"] });
let dial_speed = 0;

let status = {}
status['switch_fb'] = 0;
status['switch_lr'] = 0;
status['dial_speed'] = 0;
status['switch_boot'] = 0;

socket.on('status', (message) => {
  console.log('status:' + JSON.stringify(message));
  console.log('switch_lr' + document.getElementById('switch_lr'))
  console.log('dial_speed' + document.getElementById('dial_speed'))
  document.getElementById('switch_fb').innerText = ' ' + String(message['switch_fb']);
  document.getElementById('switch_lr').innerText = ' ' + String(message['switch_lr']);
  document.getElementById('dial_speed').innerText = ' ' + String(message['dial_speed']);
  document.getElementById('switch_boot').innerText = ' ' + String(message['switch_boot']);
});

function control(){
  console.log(status);
  socket.emit('control', status);
}

function boot() {
  console.log('boot()')
  status['switch_boot'] = 54;
  control();
  window.setTimeout( bootOff, 5000 );
}

function bootOff() {
  console.log('bootOff()')
  status['switch_boot'] = 0;
  control();
}

function changeSpeed(speed){
  status['dial_speed'] = Number(speed);
  control()
}


function stop() {
  console.log('stop()')
  status['switch_fb'] = 0;
  status['switch_lr'] = 0;
  control();
}

function forward() {
  console.log('forward()')
  status['switch_fb'] = 2;
  status['switch_lr'] = 0;
  control();
}

function forwardRight() {
  console.log('forwardRight()')
  status['switch_fb'] = 2;
  status['switch_lr'] = 1;
  control();
}

function forwardLeft() {
  console.log('forwardLeft()')
  status['switch_fb'] = 2;
  status['switch_lr'] = 2;
  control();
}

function backward() {
  console.log('backward()')
  status['switch_fb'] = 1;
  status['switch_lr'] = 0;
  control();
}

function backwardRight() {
  console.log('backwardRight()')
  status['switch_fb'] = 1;
  status['switch_lr'] = 1;
  control();
}

function backwardLeft() {
  console.log('backwardLeft()')
  status['switch_fb'] = 1;
  status['switch_lr'] = 2;
  control();
}

function right() {
  console.log('right()')
  status['switch_fb'] = 0;
  status['switch_lr'] = 1;
  control();
}

function left() {
  console.log('left()')
  status['switch_fb'] = 0;
  status['switch_lr'] = 2;
  control();
}