#!/bin/bash
sudo lsof -ti tcp:5000 | xargs kill -9
sudo lsof -ti tcp:3000 | xargs kill -9
