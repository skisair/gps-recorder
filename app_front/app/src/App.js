import Axios from 'axios';
import './App.css';
import * as React from 'react';
import Paper from '@material-ui/core/Paper';
import { ViewState } from '@devexpress/dx-react-scheduler';
import {
  Scheduler,
  DayView,
  Appointments,
} from '@devexpress/dx-react-scheduler-material-ui';

const currentDate = '2018-11-01';
const schedulerData = [
  { startDate: '2018-11-01T09:45', endDate: '2018-11-01T11:00', title: 'Meeting' },
  { startDate: '2018-11-01T12:00', endDate: '2018-11-01T13:30', title: 'Go to a gym' },
];

export default () => (
    <Paper>
      <Scheduler
          data={schedulerData}
      >
        <ViewState
            currentDate={currentDate}
        />
        <DayView
            startDayHour={9}
            endDayHour={14}
        />
        <Appointments />
      </Scheduler>
    </Paper>
);

/*
//function App() {
export class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {value: ''};

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  render() {
    return (
        <div className="App">
          <header className="App-header">
            <h1>text parser</h1>
            <form onSubmit={this.handleSubmit}>
              <label>
                <textarea name="text" cols="80" rows="4" value={this.state.value} onChange={this.handleChange} />
              </label>
              <br/>
              <input type="submit" value="Parse" />
            </form>
          </header>
        </div>
    );
  }


  wakati = text => {
    //console.log("input text >>"+text)
    Axios.post('http://127.0.0.1:5000/list_device', {
      post_text: text
    }).then(function(res) {
      alert(JSON.stringify(res.data));
    })
  };

  handleSubmit = event => {
    this.wakati(this.state.value)
    event.preventDefault();
  };

  handleChange = event => {
    this.setState({ value: event.target.value });
  };
}

export default App;
*/