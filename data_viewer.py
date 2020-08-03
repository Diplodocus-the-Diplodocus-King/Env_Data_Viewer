# DATA VIEWER
# This is a basic application to view the allotment environmental data.

# First, import all core modules - sys here allows the passing of acutal script augments to QApplication

import sys
import csv
import resources
import glob
from collections import deque
from PyQt5 import QtChart as qtch
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc

# next create a main window class - NOTE the difference here between the standard template and the one for a main window is the call to QWidget and QMainWindow in the class definition
# NOTE - here the class QWidget is made into a sub class and the constructor method is overridden.
# this is the recommended way to approach Qt GUI building as it allows customisation and expansion on Qt's powerful widget classes.
# in many cases subclassing is the only way to utilise certain classes or accomplish certain customizations
# NOTE - always call super().__init__() inside your child class's constructor, especially with Qt classes as it will cause errors.

class MainWindow(qtw.QMainWindow):
    
    def __init__(self):
        """MainWindow constructor"""
        super().__init__()

        self.setWindowTitle('Allotment Environmental Data Viewer v0.3')

        # Create the tab widget
        tabs = qtw.QTabWidget()
        self.setCentralWidget(tabs)

        self.statSheet = Statistics()
        statsIdx = tabs.addTab(self.statSheet, '')

        self.tempPlot = Plot(1)
        tempIdx = tabs.addTab(self.tempPlot, '')

        self.pressurePlot = Plot(2)
        pressureIdx = tabs.addTab(self.pressurePlot, '')

        self.humidityPlot = Plot(3)
        humidityIdx = tabs.addTab(self.humidityPlot, '')

        self.luxPlot = Plot(7)
        luxIdx = tabs.addTab(self.luxPlot, '')

        # set icons for tabs
        statsIcon = qtg.QIcon(':/plots/stats.png')
        tempIcon = qtg.QIcon(':/plots/temperature.png')
        pressureIcon = qtg.QIcon(':/plots/pressure.png')
        humidityIcon = qtg.QIcon(':/plots/humidity.png')
        luxIcon = qtg.QIcon(':/plots/lux.png')
        tabs.setTabIcon(statsIdx, statsIcon)
        tabs.setTabIcon(tempIdx, tempIcon)
        tabs.setTabIcon(pressureIdx, pressureIcon)
        tabs.setTabIcon(humidityIdx, humidityIcon)
        tabs.setTabIcon(luxIdx, luxIcon)
        tabs.setIconSize(qtc.QSize(32, 32))

        #tabs.setTabShape(qtw.QTabWidget.Triangular)
        
        # Creating a dock widget for data analysis controls
        dock = qtw.QDockWidget('Data Analysis')
        self.addDockWidget(qtc.Qt.TopDockWidgetArea, dock)
        dock.setFeatures(qtw.QDockWidget.NoDockWidgetFeatures)

        # Add the QWidget container to the dock widget
        analysisWidget = qtw.QWidget()
        dock.setWidget(analysisWidget)

        # Create the layout widget and add it to the QWidget
        gridLayout = qtw.QGridLayout()
        analysisWidget.setLayout(gridLayout)

        # Create widget objects
        startLabel = qtw.QLabel('Select Start Date:', self)
        endLabel = qtw.QLabel('Select Period:', self)
        self.windowRangeLabel = qtw.QLabel('Please select a start date...')
        yearCompLabel = qtw.QLabel('Select historical comparison range:')
        dataCompLabel = qtw.QLabel('Select additional data to overlay:')

        self.goButton = qtw.QPushButton('GO', clicked = self.replotter)
        self.goButton.setShortcut(qtg.QKeySequence('enter'))

        # Limit maximum date time to the end of the month the data is present for
        csvFiles = []
        for file in glob.glob("C:/Users/Diplodocus/Desktop/python_code/Farm Management App/Env_Data/*.csv"):
            csvFiles.append(qtc.QDateTime.toMSecsSinceEpoch(qtc.QDateTime.fromString(file[-12:-9] + ' ' + file[-8:-4], 'MMM yyyy')))

        csvFiles = sorted(csvFiles)
        latestAvailableData = qtc.QDateTime.fromMSecsSinceEpoch(csvFiles[-1])
        
        self.maximumDateTime = latestAvailableData.addMonths(1)
        self.maximumDateTime = self.maximumDateTime.addSecs(-60*30)

        self.startDateTimeBox = qtw.QDateTimeEdit(
            self,
            dateTime = latestAvailableData,
            calendarPopup = True,
            maximumDateTime = self.maximumDateTime,
            minimumDateTime = qtc.QDateTime(2020, 2, 1, 15, 30),
            displayFormat = 'dd/MM/yyyy'
        )

        self.endDateTimeBox = qtw.QComboBox(self, editable = False)
        self.endDateTimeBox.addItem('Day', 1)
        # self.endDateTimeBox.addItem('3 Days', 3)
        # self.endDateTimeBox.addItem('Week', 7)
        # self.endDateTimeBox.addItem('Fortnight', 14)
        # self.endDateTimeBox.addItem('Month', 30)
        # self.endDateTimeBox.addItem('Season', 90)

        self.yearCompSpinbox = qtw.QSpinBox(
            self, 
            value = qtc.QDate.currentDate().year(),
            maximum = qtc.QDate.currentDate().year(),
            minimum = 2020,
            singleStep = 1
        )

        self.dataCompCombobox = qtw.QComboBox(self, editable = False)
        self.dataCompCombobox.addItem('Temperature', 1)
        self.dataCompCombobox.addItem('Pressure', 2)
        self.dataCompCombobox.addItem('Humidity', 3)
        self.dataCompCombobox.addItem('Luminosity', 4)

        # Add widgets to the layout
        gridLayout.addWidget(startLabel, 0, 0)
        gridLayout.addWidget(endLabel, 0, 1)
        gridLayout.addWidget(self.startDateTimeBox, 1, 0)
        gridLayout.addWidget(self.endDateTimeBox, 1, 1)
        gridLayout.addWidget(self.windowRangeLabel, 1, 2)
        gridLayout.addWidget(yearCompLabel, 2, 0)
        gridLayout.addWidget(dataCompLabel, 2, 1)
        gridLayout.addWidget(self.yearCompSpinbox, 3, 0)
        gridLayout.addWidget(self.dataCompCombobox, 3, 1)
        gridLayout.addWidget(self.goButton, 1, 2, 4, 1)

        # Create status bar
        self.statusBar()

        self.plotInfo = qtw.QLabel('Min: 0   Max: 0   Avg: 0')
        self.statusBar().addPermanentWidget(self.plotInfo)
        # NOTE - need to add update function when new data is called and a new tab is selected.

        # Set up signals and slots
        # Prevent end date being earlier in time than start date, also fixes max data view to 3 months
        self.startDateTimeBox.dateTimeChanged.connect(self.minEndDateTimeModifier)

        self.show()

    @qtc.pyqtSlot(qtc.QDateTime)
    def minEndDateTimeModifier(self, startDateTime):

        maxDateTime = qtc.QDateTime.toMSecsSinceEpoch(self.maximumDateTime)
        selectedDateTime = qtc.QDateTime.toMSecsSinceEpoch(startDateTime)

        # get the window for possible data in minutes
        dateTimeWindow = (maxDateTime - selectedDateTime)/(1000*3600*24)

        for i in list(range(5, -1, -1)):
            self.endDateTimeBox.removeItem(i)

        if dateTimeWindow < 1:
            
            self.goButton.setDisabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date!')

        elif dateTimeWindow >= 1 and dateTimeWindow < 3:

            self.endDateTimeBox.addItem('Day', 1)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date to view a larger data range...')

        elif dateTimeWindow >= 3 and dateTimeWindow < 7:

            self.endDateTimeBox.addItem('Day', 1)
            self.endDateTimeBox.addItem('3 Days', 3)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date to view a larger data range...')

        elif dateTimeWindow >= 7 and dateTimeWindow < 14:

            self.endDateTimeBox.addItem('Day', 1)
            self.endDateTimeBox.addItem('3 Days', 3)
            self.endDateTimeBox.addItem('Week', 7)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date to view a larger data range...')

        elif dateTimeWindow >= 14 and dateTimeWindow < 31:

            self.endDateTimeBox.addItem('Day', 1)
            self.endDateTimeBox.addItem('3 Days', 3)
            self.endDateTimeBox.addItem('Week', 7)
            self.endDateTimeBox.addItem('Fortnight', 14)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date to view a larger data range...')

        elif dateTimeWindow >= 31 and dateTimeWindow < 92:  # NOTE - this function can be changed to ensure feb data is available at 28 days

            self.endDateTimeBox.addItem('Day', 1)
            self.endDateTimeBox.addItem('3 Days', 3)
            self.endDateTimeBox.addItem('Week', 7)
            self.endDateTimeBox.addItem('Fortnight', 14)
            self.endDateTimeBox.addItem('Month', 30)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Please choose an earlier date to view a larger data range...')

        # TODO - this current set up ensure data will be available for the extreme case i.e. max 3 month period = 92 days
        # the above if statements also covers the extreme for the month option i.e. 31 days
        # this will need to be modified to cover all particular caveats i.e. for certain 3 month periods and months with less than 31 days 
        else:  

            self.endDateTimeBox.addItem('Day', 1)
            self.endDateTimeBox.addItem('3 Days', 3)
            self.endDateTimeBox.addItem('Week', 7)
            self.endDateTimeBox.addItem('Fortnight', 14)
            self.endDateTimeBox.addItem('Month', 30)
            self.endDateTimeBox.addItem('Season', 90)
            self.goButton.setEnabled(True)
            self.windowRangeLabel.setText('Note: Max data viewing range is 3 months')

    @qtc.pyqtSlot()
    def replotter(self):

        startDateTime = self.startDateTimeBox.dateTime()
        endDateTimeIdx = self.endDateTimeBox.itemData(self.endDateTimeBox.currentIndex())

        if endDateTimeIdx <= 14:
            endDateTime = startDateTime.addDays(endDateTimeIdx)
        elif endDateTimeIdx == 30:
            endDateTime = startDateTime.addMonths(1)
        else:
            endDateTime = startDateTime.addMonths(3)

        self.tempPlot.refreshData(1, startDateTime, endDateTime)
        self.pressurePlot.refreshData(2, startDateTime, endDateTime)
        self.humidityPlot.refreshData(3, startDateTime, endDateTime)
        self.luxPlot.refreshData(7, startDateTime, endDateTime)
        self.statSheet.refreshData(startDateTime, endDateTime)
        self.plotInfo.setText(self.statSheet.statusBarData())

class CsvReader():
    """The model for a CSV table."""

    def __init__(self, startDateTime, endDateTime):
        super().__init__()

        # Do first read in of data file based on start date
        fileDateTimeStr = qtc.QDateTime.toString(startDateTime, 'MMM yyyy')
        filename = 'c:/Users/Diplodocus/Desktop/python_code/Farm Management App/Env_Data/PT_{0}_{1}.CSV'.format(fileDateTimeStr[0:3], fileDateTimeStr[4:8])

        with open(filename) as fh:
            csvReader = csv.reader(fh)
            self._headers = next(csvReader)
            self._data = list(csvReader)

    def newRequest(self, startDateTime, endDateTime):

        startMonthInt = int(qtc.QDateTime.toString(startDateTime, 'MM'))
        endMonthInt = int(qtc.QDateTime.toString(endDateTime, 'MM'))

        startDateTimeStr = qtc.QDateTime.toString(startDateTime, 'dd/MM/yyyy hh:mm')
        endDateTimeStr = qtc.QDateTime.toString(endDateTime, 'dd/MM/yyyy hh:mm')

        fileDateTime = startDateTime
        fileDateTimeStr = qtc.QDateTime.toString(fileDateTime, 'MMM yyyy')
        filename = 'c:/Users/Diplodocus/Desktop/python_code/Farm Management App/Env_Data/PT_{0}_{1}.CSV'.format(fileDateTimeStr[0:3], fileDateTimeStr[4:8])

        with open(filename) as fh:
            csvReader = csv.reader(fh)
            self._headers = next(csvReader)
            plotData = list(csvReader)

        # If start date month and end date month are not the same run through loop and collect data
        while startMonthInt != endMonthInt:

            startMonthInt += 1
            fileDateTime = fileDateTime.addMonths(1)

            # Catch year end
            if startMonthInt == 13:
                startMonthInt = 1

            fileDateTimeStr = qtc.QDateTime.toString(fileDateTime, 'MMM yyyy')
            filename = 'c:/Users/Diplodocus/Desktop/python_code/Farm Management App/Env_Data/PT_{0}_{1}.CSV'.format(fileDateTimeStr[0:3], fileDateTimeStr[4:8])

            with open(filename) as fh:
                csvReader = csv.reader(fh)
                self._headers = next(csvReader)
                newData = list(csvReader)

            for row in newData:
                plotData.append(row)

        startIdx = None
        endIdx = None

        #NOTE - this needs to be amended so that if a value isn't return due to missing data it finds the nearest data
        while startIdx == None:
            for row in self._data:
                if row[0] == startDateTimeStr:
                    startIdx = plotData.index(row)
                    break

                elif row == plotData[-1]:

                    startDateTime = qtc.QDateTime.fromString(endDateTimeStr, 'dd/MM/yyyy hh:mm')
                    startDateTime = endDateTime.addSecs(1800)
                    startDateTimeStr = qtc.QDateTime.toString(endDateTime, 'dd/MM/yyyy hh:mm')


        while endIdx == None:
            for row in plotData:
                if row[0] == endDateTimeStr:
                    endIdx = plotData.index(row)
                    break
                elif row == plotData[-1]:

                    endDateTime = qtc.QDateTime.fromString(endDateTimeStr, 'dd/MM/yyyy hh:mm')
                    endDateTime = endDateTime.addSecs(1800)
                    endDateTimeStr = qtc.QDateTime.toString(endDateTime, 'dd/MM/yyyy hh:mm')

        plotData = plotData[startIdx:endIdx]

        return(plotData)

  
# Temperature graph class
class Plot(qtch.QChartView):

    def __init__(self, idx):
        super().__init__()

        startDateTime = qtc.QDateTime(2020, 2, 1, 15, 30)
        endDateTime = qtc.QDateTime(2020, 2, 1, 16, 00)

        chartTitle = CsvReader(startDateTime, endDateTime)._headers[idx]
        seriesTitle = chartTitle.split()[0]

        # Create QChart object
        chart = qtch.QChart(title=chartTitle)
        self.setChart(chart)

        # Create series object
        self.series = qtch.QSplineSeries(name=seriesTitle)
        chart.addSeries(self.series)
        #self.series.setColor(qtg.QColor('red'))

        if idx == 7:
            self.irSeries = qtch.QSplineSeries(name='Infrared')
            chart.addSeries(self.irSeries)
            self.visSeries = qtch.QSplineSeries(name='Visible Light')
            chart.addSeries(self.visSeries)
            self.fsSeries = qtch.QSplineSeries(name='Full Spectrum')
            chart.addSeries(self.fsSeries)

        # setup the axes
        self.xAxis = qtch.QDateTimeAxis()
        self.yAxis = qtch.QValueAxis()
        chart.setAxisX(self.xAxis, self.series)
        chart.setAxisY(self.yAxis, self.series)

        if idx == 7:
            chart.setAxisX(self.xAxis, self.irSeries)
            chart.setAxisY(self.yAxis, self.irSeries)
            chart.setAxisX(self.xAxis, self.visSeries)
            chart.setAxisY(self.yAxis, self.visSeries)
            chart.setAxisX(self.xAxis, self.fsSeries)
            chart.setAxisY(self.yAxis, self.fsSeries)

        # As we are using curves there is one appearance optimization to do:
        self.setRenderHint(qtg.QPainter.Antialiasing)       

    # Define the refresh method
    def refreshData(self, idx, startDateTime, endDateTime):

        self.series.clear()

        # Grab data
        envData = CsvReader(startDateTime, endDateTime)
        self.plotData = envData.newRequest(startDateTime, endDateTime)
    
        # Draw in data
        if idx == 7:

            self.irSeries.clear()
            self.visSeries.clear()
            self.fsSeries.clear()

            for row in self.plotData:

                irVal = float(row[idx-3])
                visVal = float(row[idx-2])
                fsVal = float(row[idx-1])
                luxVal = float(row[idx])
                timeVal = qtc.QDateTime.fromString(row[0], 'dd/MM/yyyy hh:mm').toMSecsSinceEpoch()

                self.series.append(timeVal, luxVal) 
                self.irSeries.append(timeVal, irVal)
                self.visSeries.append(timeVal, visVal)
                self.fsSeries.append(timeVal, fsVal)
        else:
            for row in self.plotData:

                dataVal = float(row[idx])
                timeVal = qtc.QDateTime.fromString(row[0], 'dd/MM/yyyy hh:mm').toMSecsSinceEpoch()

                self.series.append(timeVal, dataVal) 

        # Set axis ranges
        timeLength = int(startDateTime.secsTo(endDateTime)/(3600*24))

        # TODO - Sort out x axis labels 
        if timeLength == 1:
            self.xAxis.setTickCount(25)
            self.xAxis.setFormat('hh:mm')
        elif timeLength == 3:
            self.xAxis.setTickCount(36)
            self.xAxis.setFormat('hap')
        elif timeLength == 7:
            self.xAxis.setTickCount(28)
            self.xAxis.setFormat('d hap')
        elif timeLength == 14:
            self.xAxis.setTickCount(28)
            self.xAxis.setFormat('d hap')
        elif timeLength > 14 and timeLength <= 31:
            self.xAxis.setTickCount(timeLength) 
            self.xAxis.setFormat('d') 
        else:
            self.xAxis.setTickCount(timeLength/3)   
            self.xAxis.setFormat('d MMM')   
        # self.xAxis.setTickCount(timeLength/(timeLength*0.05)) # 0.0417 is ideal but font size means its cut off
        self.xAxis.setRange(startDateTime, endDateTime)

        # format axis based on time window i.e. only show hh:mm for less than a day
        # if timeLength <= 1:
        #     self.xAxis.setFormat('hh:mm')
        
        # else:
        #     self.xAxis.setFormat('dd MMM (hh:mm)')

        if idx == 1:
            self.yAxis.setRange(-5, 50)
            self.yAxis.setTickType(0)
            self.yAxis.setTickAnchor(-5)
            self.yAxis.setTickInterval(5)
        elif idx == 2:
            self.yAxis.setRange(95000, 105000)
            self.yAxis.setTickType(0)
            self.yAxis.setTickAnchor(95000)
            self.yAxis.setTickInterval(500)
        elif idx == 3:
            self.yAxis.setRange(0, 100)
            self.yAxis.setTickType(0)
            self.yAxis.setTickAnchor(0)
            self.yAxis.setTickInterval(5)
        elif idx == 7:
            self.yAxis.setRange(0, 90000)
            self.yAxis.setTickType(0)
            self.yAxis.setTickAnchor(0)
            self.yAxis.setTickInterval(5000)

    # We can enable the user to pan around the chart by overriding the keyPressEvent() method in the QChart Object
    def keyPressEvent(self, event):
        keymap = {
            qtc.Qt.Key_Up: lambda: self.chart().scroll(0, -10),
            qtc.Qt.Key_Down: lambda: self.chart().scroll(0, 10),
            qtc.Qt.Key_Right: lambda: self.chart().scroll(-10, 0),
            qtc.Qt.Key_Left: lambda: self.chart().scroll(10, 0),
            qtc.Qt.Key_Greater: self.chart().zoomIn,
            qtc.Qt.Key_Less: self.chart().zoomOut
        }
        callback = keymap.get(event.key())
        if callback:
            callback()

class Statistics(qtw.QWidget):

    def __init__(self):

        super().__init__()

        # create container widget and layout
        gridLayout = qtw.QGridLayout()

        self.setLayout(gridLayout)

        gridLayout.setContentsMargins(0, 0, 0, 0)
        gridLayout.setSpacing(0)

        # Create widget objects
        dayTempLabel = qtw.QLabel('Min/Max/Average Day Temperature (*C)', self)
        self.dayTempRangeLabel = qtw.QLabel('Selected Range', self)
        dayTempSeasonLabel = qtw.QLabel('Season', self)

        nightTempLabel = qtw.QLabel('Min/Max/Average Day Temperature (*C)', self)
        self.nightTempRangeLabel = qtw.QLabel('Selected Range', self)
        nightTempSeasonLabel = qtw.QLabel('Season', self)

        sunnyDaysLabel = qtw.QLabel('Number of Sunny Days', self)
        sunnyDaysRangeLabel = qtw.QLabel('Selected Range', self)
        sunnyDaysSeasonLabel = qtw.QLabel('Season', self)

        dayLightLabel = qtw.QLabel('Average Day Light Hours', self)
        dayLightRangeLabel = qtw.QLabel('Selected Range', self)
        dayLightSeasonLabel = qtw.QLabel('Season', self)

        lastFrostLabel = qtw.QLabel('Last Frost Date', self)
        lastFrostYearLabel = qtw.QLabel('Selected Year', self)
        lastFrostLifetimeLabel = qtw.QLabel('Lifetime Average', self)

        firstFrostLabel = qtw.QLabel('First Frost Date', self)
        firstFrostYearLabel = qtw.QLabel('Selected Year', self)
        firstFrostLifetimeLabel = qtw.QLabel('Lifetime Average', self)

        # Add widgets to layout
        gridLayout.addWidget(dayTempLabel, 0, 0)
        gridLayout.addWidget(self.dayTempRangeLabel, 1, 0)
        gridLayout.addWidget(dayTempSeasonLabel, 2, 0)

        gridLayout.addWidget(nightTempLabel, 3, 0)
        gridLayout.addWidget(self.nightTempRangeLabel, 4, 0)
        gridLayout.addWidget(nightTempSeasonLabel, 5, 0)

        gridLayout.addWidget(sunnyDaysLabel, 0, 1)
        gridLayout.addWidget(sunnyDaysRangeLabel, 1, 1)
        gridLayout.addWidget(sunnyDaysSeasonLabel, 2, 1)

        gridLayout.addWidget(dayLightLabel, 3, 1)
        gridLayout.addWidget(dayLightRangeLabel, 4, 1)
        gridLayout.addWidget(dayLightSeasonLabel, 5, 1)

        gridLayout.addWidget(lastFrostLabel, 0, 2)
        gridLayout.addWidget(lastFrostYearLabel, 1, 2)
        gridLayout.addWidget(lastFrostLifetimeLabel, 2, 2)

        gridLayout.addWidget(firstFrostLabel, 3, 2)
        gridLayout.addWidget(firstFrostYearLabel, 4, 2)
        gridLayout.addWidget(firstFrostLifetimeLabel, 5, 2)

        # Format the shape of the layout, not exactly the best way to do this
        gridLayout.setRowMinimumHeight(6, 600)
        gridLayout.setColumnMinimumWidth(3, 600)
        gridLayout.setRowMinimumHeight(0, 50)
        gridLayout.setRowMinimumHeight(3, 50)


    def refreshData(self, startDateTime, endDateTime):

        envData = CsvReader(startDateTime, endDateTime)
        self.plotData = envData.newRequest(startDateTime, endDateTime)

        dayTempData = []
        nightTempData = []

        for row in self.plotData:
            if float(row[7]) > 40.0: # set to 40 based on wiki lux at sunrise for fully overcast day (for a clear day it is 400)
                dayTempData.append(float(row[1]))
            else:
                nightTempData.append(float(row[1]))

        dayMinString = '{:.2f}'.format(min(dayTempData))
        dayMaxString = '{:.2f}'.format(max(dayTempData))
        dayAvgString = '{:.2f}'.format(sum(dayTempData)/len(dayTempData))
        nightMinString = '{:.2f}'.format(min(nightTempData))
        nightMaxString = '{:.2f}'.format(max(nightTempData))
        nightAvgString = '{:.2f}'.format(sum(nightTempData)/len(nightTempData))

        dayTempRange = f'Min: {dayMinString}   Max: {dayMaxString}   Average: {dayAvgString}'
        nightTempRange = f'Min: {nightMinString}   Max: {nightMaxString}   Average: {nightAvgString}'

        self.dayTempRangeLabel.setText(dayTempRange)
        self.nightTempRangeLabel.setText(nightTempRange)

    def statusBarData(self):

        data = []

        for row in self.plotData:
            data.append(float(row[1]))

        minString = '{:.2f}'.format(min(data))
        maxString = '{:.2f}'.format(max(data))
        avgString = '{:.2f}'.format(sum(data)/len(data))

        plotInfoStr = f'Min: {minString}   Max: {maxString}   Average: {avgString}'

        return plotInfoStr

# The main code execution

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    windowsStyle = qtw.QStyleFactory.create('Fusion')
    app.setStyle(windowsStyle)
    mw = MainWindow()
    sys.exit(app.exec())

# NOTE - passing sys.argv into the QApplication object allows for debugging or altering of styles and themes.
# NOTE - app.exec() is called inside a call to sys.exit. This passes the exit code of app.exec to sys.exit so that the OS can exit the application if it crashes

