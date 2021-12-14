let socket = io.connect('/web-ctl',{ transports: ["polling"] });
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

socket.on('signal', function(message){
  console.log('signal:' + JSON.stringify(message));
  document.getElementById('signal').innerText = message.signal;
});

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

let camera_connected = false;

function camera(){
  if(camera_connected){
    disconnect();
    document.getElementById("camera").src = "/static/image/camera.png";
    camera_connected = false;
  }else{
    connect();
    document.getElementById("camera").src = "/static/image/camera_on.png";
    camera_connected = true;
  }

}

function boot() {
  console.log('boot()')
  status['switch_boot'] = 54;
  control();
  window.setTimeout( bootOff, 3000 );
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

function right_90() {
  console.log('right_90()')
  status['switch_fb'] = 0;
  status['switch_lr'] = 1;
  control();
  window.setTimeout( bootOff, 5000 );
}

function left_90() {
  console.log('left_90()')
  status['switch_fb'] = 0;
  status['switch_lr'] = 2;
  control();
  window.setTimeout( bootOff, 5000 );
}

let last_update = 0;

// 匿名関数を即時実行
(function(){
  // ------------------------------------------------------------
  // Gemapad API に対応しているか調べる
  // ------------------------------------------------------------
  if(!(window.Gamepad)) return;
  if(!(navigator.getGamepads)) return;

  // ------------------------------------------------------------
  // 一定時間隔で、繰り返し実行される関数
  // ------------------------------------------------------------
  setInterval(function(){
    let switch_fb = status['switch_fb'];
    let switch_lr = status['switch_lr'];
    var str = "";
    // ゲームパッドリストを取得する
    var gamepad_list = navigator.getGamepads();
    // ゲームパッドリスト内のアイテム総数を取得する
    var num = gamepad_list.length;
    var i;
    for(i=0;i < num;i++){
      // ------------------------------------------------------------
      // Gamepad オブジェクトを取得する
      // ------------------------------------------------------------
      var gamepad = gamepad_list[i];
      if(!gamepad) continue;

      let buttons = gamepad.buttons;
      if(buttons[2].pressed){ // ■
        boot();
      }
      if(gamepad.timestamp - last_update > 0.5){
        if(buttons[1].pressed){ // 〇
          camera();
          last_update = gamepad.timestamp;
        }

        if(buttons[15].pressed){ // 右
          dial_speed = dial_speed + 1;
          if(dial_speed > 5){
            dial_speed = 5;
          }
          changeSpeed(dial_speed)
          last_update = gamepad.timestamp;
        }
        if(buttons[14].pressed){ // 左
          dial_speed = dial_speed - 1;
          if(dial_speed < 0){
            dial_speed = 0;
          }
          changeSpeed(dial_speed)
          last_update = gamepad.timestamp;
        }
      }

      let axes = gamepad.axes;
      if(axes[3] > 0.25){
        status['switch_fb'] = 1;
      }else if(axes[3] < -0.25) {
        status['switch_fb'] = 2;
      }else {
        status['switch_fb'] = 0;
      }

      if(axes[2] > 0.25){
        status['switch_lr'] = 1;
      }else if(axes[2] < -0.25) {
        status['switch_lr'] = 2;
      }else {
        status['switch_lr'] = 0;
      }
      if((switch_fb == status['switch_fb']) && (switch_lr == status['switch_lr'])){
        //console.log('pass');
      } else {
        control();
      }
    }
    //sleep(0.1)
    // console.log(str);

  },1000/5);

})();