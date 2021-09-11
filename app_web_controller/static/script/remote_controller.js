let socket = io.connect({ transports: ["polling"] });
let dial_speed = 0;

let status = {}
status['switch_fb'] = 0;
status['switch_lr'] = 0;
status['dial_speed'] = 0;
status['switch_boot'] = 0;

const NEUTRAL = 0
const MOVE_FORWARD = 2
const MOVE_BACKWARD = 1
const TURN_LEFT = 2
const TURN_RIGHT = 1
const BOOT = 54

function generateUuid() {
  // https://github.com/GoogleChrome/chrome-platform-analytics/blob/master/src/internal/identifier.js
  // const FORMAT: string = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
  let chars = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".split("");
  for (let i = 0, len = chars.length; i < len; i++) {
    switch (chars[i]) {
      case "x":
        chars[i] = Math.floor(Math.random() * 16).toString(16);
        break;
      case "y":
        chars[i] = (Math.floor(Math.random() * 4) + 8).toString(16);
        break;
    }
  }
  return chars.join("");
}

const uuid = generateUuid();

status['uuid'] = uuid;

socket.on('status', (message) => {

  console.log('status:' + JSON.stringify(message));
  if(message['uuid'] == uuid){
    console.log('perf:' + (performance.now() - message['time']).toFixed(1) + ' ms');
  }

  if(message['switch_fb'] == MOVE_FORWARD){
    document.getElementById('forward').src = "/static/image/forward_on.png";
    document.getElementById('backward').src = "/static/image/backward.png";
  }else if(message['switch_fb'] == MOVE_BACKWARD){
    document.getElementById('forward').src = "/static/image/forward.png";
    document.getElementById('backward').src = "/static/image/backward_on.png";
  }else{
    document.getElementById('forward').src = "/static/image/forward.png";
    document.getElementById('backward').src = "/static/image/backward.png";
  }

  if(message['switch_lr'] == TURN_LEFT){
    document.getElementById('left').src = "/static/image/left_on.png";
    document.getElementById('right').src = "/static/image/right.png";
  }else if(message['switch_lr'] == TURN_RIGHT){
    document.getElementById('left').src = "/static/image/left.png";
    document.getElementById('right').src = "/static/image/right_on.png";
  }else{
    document.getElementById('left').src = "/static/image/left.png";
    document.getElementById('right').src = "/static/image/right.png";
  }

  if(message['switch_boot'] == BOOT){
    document.getElementById('button').src = "/static/image/button_on.png";
  } else {
    document.getElementById('button').src = "/static/image/button.png";
  }
  document.getElementById('slide').value = message['dial_speed'];
});

function control(){
  status['time'] = performance.now();
  console.log('control:' + JSON.stringify(status));
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